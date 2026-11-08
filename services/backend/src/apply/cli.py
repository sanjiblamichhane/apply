"""
The ``apply`` command:

    apply migrate                       bring the database up to date
    apply init [--email …]              create the owner account (asks for a password)
    apply password [--email …]          a new password for an account (when no email can be sent)
    apply serve [--no-migrate]          the API on APPLY_HOST:APPLY_PORT (127.0.0.1:8110)
    apply worker [--queue llm] [--concurrency 1] [--once]
    apply check-model                   is the model server there, with the models?
    apply openapi [--out FILE]          the API's OpenAPI schema
    apply mcp                           an MCP server on stdio, for AI agents (APPLY_TOKEN, APPLY_URL)
    apply demo [--email …] [--force]    a demo account to look around in (no model needed)

Messages are in any of apply's languages: APPLY_LANG=es (or ne, zh, …), else the system's locale, else English.
"""

import argparse
import asyncio
import getpass
import json
import logging
import sys
from pathlib import Path

from apply import __version__
from apply.errors import ApplyError, ErrorCode
from apply.i18n import LOCALES, t
from apply.settings import AppSettings


def _settings() -> AppSettings:
    try:
        return AppSettings()
    except ValueError as exc:
        sys.exit(str(exc))


def cmd_migrate(_args: argparse.Namespace) -> int:
    from apply.store.sql import migrate

    migrate(_settings().database_url)
    print(t("migrate.done"))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    from apply.logic.auth import MIN_PASSWORD, create_owner
    from apply.store.sql import Database
    from apply.store.sql.migrate import head, is_current

    settings = _settings()
    if not is_current(settings.database_url) and head():
        print(t("db.not_ready"), file=sys.stderr)
        return 2
    email = args.email or input(t("init.email"))
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass(t("init.password"))
        if password != getpass.getpass(t("init.password_again")):
            print(t("init.password_mismatch"), file=sys.stderr)
            return 1
    if len(password) < MIN_PASSWORD:
        print(t("init.password_short"), file=sys.stderr)
        return 1

    async def create() -> None:
        db = Database(settings.database_url)
        try:
            await create_owner(db, email, password, locale=args.locale)
        finally:
            await db.dispose()

    try:
        asyncio.run(create())
    except ApplyError as exc:
        if exc.code == ErrorCode.OWNER_EXISTS:
            print(t("init.owner_exists"), file=sys.stderr)
            return 1
        print(exc.detail, file=sys.stderr)
        return 1
    print(t("init.done", email=email.strip().lower()))
    return 0


def cmd_password(args: argparse.Namespace) -> int:
    """A new password for an account, when no email can be sent; it's signed out everywhere."""
    from apply.logic.auth import MIN_PASSWORD, set_password
    from apply.store.sql import Database

    settings = _settings()
    email = (args.email or input(t("password.email"))).strip().lower()
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass(t("password.choose"))
        if password != getpass.getpass(t("init.password_again")):
            print(t("password.mismatch"), file=sys.stderr)
            return 1
    if len(password) < MIN_PASSWORD:
        print(t("password.short"), file=sys.stderr)
        return 1

    async def change() -> None:
        db = Database(settings.database_url)
        try:
            await set_password(db, email, password)
        finally:
            await db.dispose()

    try:
        asyncio.run(change())
    except ApplyError as exc:
        if exc.code == ErrorCode.NOT_FOUND:
            print(t("password.no_account", email=email), file=sys.stderr)
            return 1
        print(exc.detail, file=sys.stderr)
        return 1
    print(t("password.done", email=email))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from apply.app import create_app
    from apply.store.sql import migrate

    settings = _settings()
    if not args.no_migrate:
        migrate(settings.database_url)
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        proxy_headers=False,
        server_header=False,
        log_level=args.log_level,
    )
    return 0


def cmd_worker(args: argparse.Namespace) -> int:
    from apply.logic.background import QUEUES
    from apply.runtime import Runtime
    from apply.worker import run

    settings = _settings()
    queues = args.queue or list(QUEUES)
    rt = Runtime.create(settings)

    async def main() -> None:
        try:
            await run(rt, queues=queues, concurrency=args.concurrency, once=args.once)
        finally:
            await rt.aclose()

    if not args.once:
        print(t("worker.started", name="apply", queues=", ".join(queues), concurrency=args.concurrency))
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    if not args.once:
        print(t("worker.stopped"))
    return 0


async def _model_in_use(settings: AppSettings):
    """The chosen model (Settings → Model), or the settings' if none is chosen or the database isn't there."""
    from apply.logic import model_choice
    from apply.store.sql import Database

    db = Database(settings.database_url)
    try:
        return await model_choice.current(db, settings)
    except Exception:  # noqa: BLE001 - checking the model mustn't need the database
        return model_choice.Current(choice=model_choice.from_settings(settings), source="settings")
    finally:
        await db.dispose()


def cmd_check_model(_args: argparse.Namespace) -> int:
    from apply.libs.llm import client_for

    settings = _settings()

    async def check():
        in_use = await _model_in_use(settings)
        model = client_for(in_use.choice, timeout=settings.llm_timeout)
        try:
            return in_use.choice, await model.check()
        finally:
            await model.aclose()

    choice, result = asyncio.run(check())
    if not result.reachable:
        print(t("model.unreachable", url=result.base_url), file=sys.stderr)
        return 2
    if result.missing:
        print(t("model.missing", url=result.base_url, models=", ".join(result.missing)), file=sys.stderr)
        return 1
    if choice.api == "native":
        print(t("model.ok", url=result.base_url, models=", ".join(result.wanted), num_ctx=result.num_ctx))
    else:
        print(t("model.ok_server", url=result.base_url, models=", ".join(result.wanted)))
    return 0


def cmd_models(_args: argparse.Namespace) -> int:
    """What model servers answer on this machine, their models, and which is in use."""
    from apply.logic import model_choice

    settings = _settings()

    async def look():
        return await _model_in_use(settings), await model_choice.find(settings)

    in_use, found = asyncio.run(look())
    choice = in_use.choice
    key = "models.in_use.chosen" if in_use.source == "chosen" else "models.in_use.settings"
    print(t(key, model=choice.model, url=choice.base_url))
    if not found:
        print(t("models.none"))
        return 1
    for endpoint in found:
        print(f"\n{endpoint.base_url}  [{endpoint.api}]" + (f"  ({endpoint.version})" if endpoint.version else ""))
        for m in endpoint.models:
            facts = [
                m.parameters,
                f"{m.size_bytes / 1e9:.1f} GB" if m.size_bytes else None,
                f"{m.context_length:,} ctx" if m.context_length else None,
                t("models.loaded") if m.loaded else None,
                t("models.embedding") if not m.usable else None,
            ]
            print(f"  {m.name}  " + " · ".join(f for f in facts if f))
    return 0


async def _owner_id(db, email: str | None) -> str:
    from sqlalchemy import select

    from apply.store.sql.models import User

    async with db.transaction() as session:
        stmt = select(User).where(User.email == email.strip().lower()) if email else select(User).where(User.is_owner)
        user = (await session.execute(stmt)).scalars().first()
    if user is None:
        raise SystemExit("No such account. Create the owner first: apply init")
    return user.id


def _print_report(report) -> None:
    print("created:", ", ".join(f"{v} {k}" for k, v in report.created.items()))
    print("already there:", ", ".join(f"{v} {k}" for k, v in report.already.items()))
    for problem in report.problems:
        print("skipped:", problem, file=sys.stderr)


def cmd_token(args: argparse.Namespace) -> int:
    """A personal API token for the extension or an AI agent (``apply mcp``), printed once."""
    from apply.logic import tokens
    from apply.store.sql import Database

    settings = _settings()
    scopes = tokens.DEFAULT_SCOPES[args.kind]
    name = args.name or ("AI agent" if args.kind == "agent" else "Extension") + " (made on the command line)"

    async def run() -> str:
        db = Database(settings.database_url)
        try:
            owner = await _owner_id(db, args.email)
            async with db.transaction() as session:
                made = await tokens.create(
                    session,
                    owner,
                    name=name,
                    kind=args.kind,
                    scopes=scopes,
                    expires_in_days=args.days or None,
                )
                return made.secret
        finally:
            await db.dispose()

    print(asyncio.run(run()))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from apply.logic import portable
    from apply.store.sql import Database

    settings = _settings()

    async def run() -> str:
        db = Database(settings.database_url)
        try:
            owner = await _owner_id(db, args.email)
            async with db.transaction() as session:
                return (await portable.export(session, owner)).model_dump_json(indent=2)
        finally:
            await db.dispose()

    data = asyncio.run(run())
    if args.out:
        Path(args.out).write_text(data + "\n", encoding="utf-8")
    else:
        sys.stdout.write(data + "\n")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    from apply.logic import portable
    from apply.store.sql import Database

    settings = _settings()
    data = portable.PortableExport.model_validate_json(Path(args.file).read_text(encoding="utf-8"))

    async def run():
        db = Database(settings.database_url)
        try:
            owner = await _owner_id(db, args.email)
            async with db.transaction() as session:
                return await portable.import_(session, owner, data)
        finally:
            await db.dispose()

    _print_report(asyncio.run(run()))
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    from apply.demo import install
    from apply.store.sql import Database
    from apply.store.sql.migrate import head, is_current

    settings = _settings()
    if not is_current(settings.database_url) and head():
        print(t("db.not_ready"), file=sys.stderr)
        return 2
    password = sys.stdin.readline().rstrip("\n") if args.password_stdin else None

    async def run():
        db = Database(settings.database_url)
        try:
            from sqlalchemy import func, select

            from apply.store.sql.models import User

            async with db.transaction() as session:
                empty = not (await session.execute(select(func.count()).select_from(User))).scalar_one()
            secret = password
            if empty and secret is None:
                secret = getpass.getpass(t("init.password"))
            return await install(db, args.email, secret, force=args.force)
        finally:
            await db.dispose()

    try:
        report = asyncio.run(run())
    except ApplyError as exc:
        if exc.code == ErrorCode.OWNER_EXISTS:
            print(t("demo.has_accounts"), file=sys.stderr)
            return 1
        print(exc.detail, file=sys.stderr)
        return 1
    _print_report(report)
    print(t("demo.done", email=args.email.strip().lower()))
    return 0


def cmd_mcp(_args: argparse.Namespace) -> int:
    """An MCP server on stdio: AI agents use apply through its API, with an agent token."""
    from apply import mcp_server

    return mcp_server.main()


def openapi_schema() -> dict:
    from apply.app import create_app
    from apply.settings import AppSettings

    # The schema doesn't depend on the database; no connection is made.
    app = create_app(AppSettings(_env_file=None, database_url="postgresql+asyncpg://openapi@localhost/none"))
    return app.openapi()


def cmd_openapi(args: argparse.Namespace) -> int:
    text = json.dumps(openapi_schema(), indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="apply", description="apply: one workspace for anything you apply for.")
    p.add_argument("--version", action="version", version=f"apply {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="bring the database up to date").set_defaults(fn=cmd_migrate)

    init = sub.add_parser("init", help="create the owner account")
    init.add_argument("--email")
    init.add_argument("--locale", choices=LOCALES, default="en")
    init.add_argument("--password-stdin", action="store_true", help="read the password from standard input")
    init.set_defaults(fn=cmd_init)

    password = sub.add_parser("password", help="set an account's password (when no email can be sent)")
    password.add_argument("--email")
    password.add_argument("--password-stdin", action="store_true", help="read the password from standard input")
    password.set_defaults(fn=cmd_password)

    serve = sub.add_parser("serve", help="run the API")
    serve.add_argument("--no-migrate", action="store_true")
    serve.add_argument("--log-level", default="info")
    serve.set_defaults(fn=cmd_serve)

    worker = sub.add_parser("worker", help="run background jobs")
    worker.add_argument(
        "--queue",
        action="append",
        choices=["llm", "default"],
        help="a queue to take jobs from (repeatable; default: all)",
    )
    worker.add_argument("--concurrency", type=int, default=1)
    worker.add_argument("--once", action="store_true", help="run what's due, then stop")
    worker.set_defaults(fn=cmd_worker)

    sub.add_parser("check-model", help="is the model reachable and pulled?").set_defaults(fn=cmd_check_model)
    sub.add_parser("models", help="the model servers and models on this machine, and which is in use").set_defaults(
        fn=cmd_models
    )

    token = sub.add_parser("token", help="make a personal API token for the extension or an agent (printed once)")
    token.add_argument("--kind", choices=["extension", "agent"], default="extension", help="agent: for apply mcp")
    token.add_argument("--name")
    token.add_argument("--days", type=int, default=0, help="expires after this many days (default: never)")
    token.add_argument("--email", help="the account (default: the owner)")
    token.set_defaults(fn=cmd_token)

    export = sub.add_parser("export", help="everything of an account, as apply-export/1 JSON")
    export.add_argument("--out")
    export.add_argument("--email", help="the account (default: the owner)")
    export.set_defaults(fn=cmd_export)

    import_ = sub.add_parser("import", help="import an apply-export/1 file (again: only new)")
    import_.add_argument("file")
    import_.add_argument("--email", help="the account (default: the owner)")
    import_.set_defaults(fn=cmd_import)

    demo = sub.add_parser(
        "demo", help="a demo account with John Doe's fictional profile and applications (no model needed)"
    )
    demo.add_argument("--email", default="demo@example.com")
    demo.add_argument("--password-stdin", action="store_true", help="read the password from standard input")
    demo.add_argument("--force", action="store_true", help="add the demo to the existing account --email")
    demo.set_defaults(fn=cmd_demo)

    sub.add_parser("mcp", help="an MCP server on stdio for AI agents (needs APPLY_TOKEN)").set_defaults(fn=cmd_mcp)

    openapi = sub.add_parser("openapi", help="print the OpenAPI schema")
    openapi.add_argument("--out")
    openapi.set_defaults(fn=cmd_openapi)
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("alembic.runtime.plugins").setLevel(logging.WARNING)
    args = parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

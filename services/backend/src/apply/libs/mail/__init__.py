"""
Sending email over SMTP: plain text, one recipient, from ``APPLY_MAIL_FROM``.

compose.yml points it at a local mail catcher (every message stays on this machine, readable at
http://127.0.0.1:8035); on a server, at the provider's SMTP relay with STARTTLS or TLS and a login. ``smtplib``
runs in a thread so the event loop never waits on the network. Tests swap ``deliver`` for a list (``outbox``).
"""

import asyncio
import smtplib
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import make_msgid

from apply.settings import AppSettings


@dataclass(frozen=True)
class Mail:
    to: str
    subject: str
    text: str


def build(settings: AppSettings, mail: Mail) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = mail.to
    message["Subject"] = mail.subject
    message["Message-ID"] = make_msgid(domain=settings.mail_from.rsplit("@", 1)[-1].strip("> ") or "apply")
    message["Auto-Submitted"] = "auto-generated"  # RFC 3834: no out-of-office replies
    message.set_content(mail.text)
    return message


def _send(settings: AppSettings, message: EmailMessage) -> None:
    context = ssl.create_default_context()
    smtp_class = smtplib.SMTP_SSL if settings.smtp_security == "tls" else smtplib.SMTP
    kwargs = {"context": context} if settings.smtp_security == "tls" else {}
    with smtp_class(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout, **kwargs) as smtp:
        if settings.smtp_security == "starttls":
            smtp.starttls(context=context)
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


# What actually sends: the network, unless a test has put something else here.
deliver: Callable[[AppSettings, EmailMessage], None] = _send


async def send(settings: AppSettings, mail: Mail) -> None:
    """Send one email. Raises (OSError, smtplib.SMTPException) when the server can't be reached or refuses it."""
    if not settings.mail_enabled:
        raise RuntimeError("No SMTP host is set (APPLY_SMTP_HOST)")
    await asyncio.to_thread(deliver, settings, build(settings, mail))

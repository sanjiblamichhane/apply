# apply's backend: the API (`apply serve`) and the worker (`apply worker`) from one image.
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY alembic.ini README.md* ./
# The demo offered at sign-up (compose passes the repo's demo/ folder as the "demo" build context).
COPY --from=demo john-doe.json ./demo/john-doe.json
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
# Pango and fontconfig: the PDF renderer prints documents with them (in apply's own fonts, libs/render/fonts).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 fontconfig \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 apply
WORKDIR /app
COPY --from=build --chown=apply:apply /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER apply
EXPOSE 8110
CMD ["apply", "serve"]

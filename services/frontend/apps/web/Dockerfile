# apply's web app, built as a standalone Next.js server. Build from services/frontend:
#   docker build -f apps/web/Dockerfile -t apply-web .
FROM node:22-slim AS build
RUN corepack enable
WORKDIR /repo
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json tsconfig.base.json ./
COPY packages ./packages
COPY apps/web ./apps/web
RUN pnpm install --frozen-lockfile --filter @apply/web...
ENV NEXT_TELEMETRY_DISABLED=1
# The backend's address is read when the server starts (rewrites), so one image works anywhere.
RUN pnpm --filter @apply/web exec next build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3310 HOSTNAME=0.0.0.0
RUN useradd --create-home --uid 10001 apply
COPY --from=build --chown=apply:apply /repo/apps/web/.next/standalone ./
COPY --from=build --chown=apply:apply /repo/apps/web/.next/static ./apps/web/.next/static
USER apply
EXPOSE 3310
CMD ["node", "apps/web/server.js"]

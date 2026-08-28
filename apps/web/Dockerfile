FROM node:22-slim AS deps

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY apps/web/package*.json ./

RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

FROM node:22-slim AS builder

ENV NEXT_TELEMETRY_DISABLED=1

ARG NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
ARG NEXT_PUBLIC_APP_NAME="AI Trading SaaS Starter Kit"
ARG NEXT_PUBLIC_SITE_URL=https://ai-trading-agent-seven.vercel.app
ARG NEXT_PUBLIC_REPOSITORY_URL=https://github.com/waqasraza123/Trading-Data-Analysis-Agent

ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL} \
    NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME} \
    NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL} \
    NEXT_PUBLIC_REPOSITORY_URL=${NEXT_PUBLIC_REPOSITORY_URL}

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ ./

RUN mkdir -p public && npm run build

FROM node:22-slim AS runner

ENV HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    PORT=3000

WORKDIR /app

COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
COPY --from=builder --chown=node:node /app/public ./public

USER node

EXPOSE 3000

CMD ["node", "server.js"]

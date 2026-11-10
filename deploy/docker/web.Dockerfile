FROM node:26-alpine AS build
RUN corepack enable
WORKDIR /src
COPY web/package.json web/pnpm-lock.yaml ./web/
COPY contracts contracts
WORKDIR /src/web
RUN pnpm install --frozen-lockfile
COPY web .
ARG VITE_API_BASE_URL=""
ARG VITE_DEMO_MODE="false"
ARG VITE_CONTACT_EMAIL
ARG VITE_OPERATOR_NAME
ARG VITE_OIDC_AUTHORITY=""
ARG VITE_OIDC_CLIENT_ID="benchline-web"
RUN pnpm build

FROM nginxinc/nginx-unprivileged:1-alpine
COPY deploy/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/docker/security-headers.inc /etc/nginx/conf.d/security-headers.inc
COPY --from=build /src/web/dist /usr/share/nginx/html
EXPOSE 8080

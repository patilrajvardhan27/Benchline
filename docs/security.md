# Security notes

How each hardening area is handled, where to look, and what is still open.

## 1. Session management

- The API is stateless: `SessionCreationPolicy.STATELESS`, bearer tokens, no cookies.
  There is no session id to fixate, so "regenerate the id after login" has nothing to apply to.
- Settings exist as a backstop if a session or cookie is ever added:
  `server.servlet.session.cookie.http-only/secure/same-site=strict`, 30 minute timeout
  (`apps/pricing-api/src/main/resources/application.yml`). If you add server sessions,
  call `changeSessionId()` on login.
- Web: the OIDC access token lives in memory only and is dropped on sign-out
  (`web/src/shared/api/auth.tsx`). Requests use `credentials: "omit"`.

## 2. API security

- Deny by default: `anyRequest().denyAll()` in `SecurityConfig`. Each route is listed.
- Public reads (catalog, price history, benchmarks, overview, config) expose only public
  CMS data. Everything else needs a scope: `prices:write`, `members:read`,
  `insights:read`, `insights:write`.
- Responses are record types built for the client. Database entities are never serialized.
- Input is validated (`jakarta.validation`), SQL is parameterized, page size is capped at 100,
  search text is escaped for `LIKE`.
- Tested in `ApiSecurityTest`: 401 without a token, 403 with the wrong scope, unknown routes denied.

## 3. Dependencies

- Lockfiles are committed (`pnpm-lock.yaml`, `uv.lock`); Gradle versions live in `gradle/libs.versions.toml`.
- CI runs Dependabot, CodeQL, Trivy (fails on critical image CVEs), gitleaks and `pnpm audit --prod`.
- Run locally: `pnpm -C web audit --prod`, `./gradlew dependencies`, `uv pip list --outdated`.
- Unused packages are removed when found (pandera was dropped for this reason).

## 4. HTTPS and cookies

- Production profile enables `redirectToHttps` (health probes excepted) and trusts forwarded headers.
- HSTS on API responses and on the web host (`web/public/_headers`, `deploy/docker/security-headers.inc`).
- The site sets no cookies. CSP restricts scripts, styles, fonts and connections to the site itself
  and upgrades insecure requests, which blocks mixed content.
- Known trade-off: `style-src-attr 'unsafe-inline'` is allowed because the UI sets CSS custom
  properties through `style` attributes for animation. Scripts stay `'self'` only.

## 5. Error handling

- All API errors are RFC 9457 `application/problem+json` (`GlobalExceptionHandler`). Unexpected
  errors are logged with the stack trace on the server and returned as a generic 500.
- `server.error.include-*` is `never`. The ML service returns a generic 500 and has its docs disabled.
- The web client maps status codes to fixed sentences and never prints server text
  (`shared/api/errors.ts`). An error boundary catches render failures.
- Tested: a thrown exception containing a connection string never reaches the response.

## Not done yet

- Rate limiting: do it at the ingress or CDN.
- Kafka inside the cluster is plaintext. Add TLS and SASL before sharing a cluster.
- No web application firewall, and no dependency allow-list for transitive packages.
- The Dockerfiles, Helm chart and Terraform have not been run end to end yet. Validate them with `docker build`, `helm lint`, `terraform validate` and a kind deploy before relying on them.

# Deployment

## Recommended: free static demo on Cloudflare

The web app runs in demo mode (`VITE_DEMO_MODE=true`) and reads a static snapshot, so it needs
no backend. Cloudflare serves static assets with no request or bandwidth charge on the free
plan, issues TLS certificates, and supports custom domains.

1. A snapshot is already committed in `web/public/demo` (built offline from real NADAC data). Rebuild or replace it as described below.
2. Create a Cloudflare account and a Pages project named `benchline` (or use Workers static assets).
3. In the GitHub repository set secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, and
   variables `CONTACT_EMAIL` and `OPERATOR_NAME`. The `deploy-web` workflow builds and publishes.
4. Headers (CSP, HSTS and the rest) come from `web/public/_headers`; unknown paths fall back to the app via `_redirects`.
5. Before publishing, replace the placeholder email in `web/public/.well-known/security.txt` and `robots.txt`.

Cloudflare is steering new projects from Pages toward Workers with static assets. Both serve this
output unchanged, but check which one the dashboard offers when you set it up.

## The full stack for free: what is realistic

| Option | Cost | Fit | Caveat |
|---|---|---|---|
| Static demo on Cloudflare | $0 | Always-on link for a portfolio | Read-only snapshot |
| Run the stack locally, record a video | $0 | Show the live event flow | Not clickable by others |
| Azure for Students credit on AKS | Credit, not free | Matches a job's Azure stack | Nodes burn credit; stop the cluster when idle |
| Oracle Cloud Always Free VM + Docker Compose | $0 on paper | Whole stack on one VM | See below |

**AKS.** The control plane is free on the Free tier, but nodes are billed. Kafka, two Spring
services, PostgreSQL and the ML service need roughly two 2 vCPU / 8 GB nodes, which is likely more
than a $100 credit covers if left running for a month (estimate, check the Azure pricing calculator).
Use `az aks stop` when you are not demoing, set a budget alert, and `terraform destroy` afterwards.
Azure for Students eligibility and the credit amount should be confirmed on Microsoft's page.

**Oracle Always Free.** Reports from 2026 say the Ampere A1 allowance was cut to 2 OCPU / 12 GB, that
getting an A1 instance is often impossible because of capacity, and that idle instances can be
reclaimed. Treat it as a bonus if you get one, not a plan.

**Managed data on free tiers.** Free PostgreSQL tiers exist (for example Neon) but their limits
change; check them before relying on one. Upstash Kafka was reportedly discontinued. Aiven advertises
a free Kafka tier that powers off when idle. None of this was verified by running it here.

## The demo snapshot

Two ways to produce `web/public/demo`. Both write the same file shapes, and the manifest says which one was used.

**Offline build (no Docker, what is committed now).** Computes benchmarks with pandas from the cleaned
NADAC data, using the same rules as the worker, and scores price changes with the ML service's own
scoring code. It does not go through the API or Kafka.

```bash
uv run --project pipelines python -m benchline_pipelines fetch --years 2025 2026
uv run --project pipelines python -m benchline_pipelines silver --contains ATORVASTATIN METFORMIN LISINOPRIL
uv run scripts/build_demo_snapshot.py
```

**Export from a running stack.** Reads the live API, so it reflects what the real event pipeline produced.

```bash
docker compose up -d --build
# load data: fetch, silver, replay, seed_synthetic (see the README)
DEV_JWT_SECRET=... uv run scripts/export_demo_snapshot.py --out web/public/demo
```

`replay` mints its own token from `DEV_JWT_SECRET`, which must match the value in `.env`.

## Kubernetes (kind or AKS)

```bash
# kind: build images locally, load them, install
helm upgrade --install benchline deploy/helm/benchline -f deploy/helm/benchline/values-kind.yaml

# AKS: infrastructure, then the deploy workflow
cd deploy/terraform && terraform init && terraform apply
```

The `deploy-aks` workflow signs in with OIDC federation, so no cloud credential is stored in GitHub.
Set repository variables from the Terraform outputs (`terraform output`).

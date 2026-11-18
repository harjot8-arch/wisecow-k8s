# Wisecow on Kubernetes

[![CI/CD](https://github.com/harjot8-arch/wisecow-k8s/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/harjot8-arch/wisecow-k8s/actions/workflows/ci-cd.yml)

AccuKnox QA Trainee practical assessment, by **Harjot Singh**.

Wisecow is a tiny Bash web server that answers every request with a random fortune said by a cow.
This repo containerises it, deploys it to Kubernetes behind HTTPS, and ships it through a CI/CD
pipeline that **deploys every commit to a real Kubernetes cluster and tests it over TLS**.

```
push to main
   │
   ├─ lint ─── ShellCheck · Hadolint · kubeconform (strict, incl. CRDs)
   ├─ test ─── ruff · pytest (18 tests) · runs both scripts
   ▼
 build ─────── docker build → smoke test (read-only FS, no capabilities, non-root)
   │           → Grype vulnerability scan → push ghcr.io/harjot8-arch/wisecow:sha-<commit>, :latest
   ▼
 deploy ────── kind cluster → cert-manager + Envoy Gateway → kubectl apply -k k8s
               → wait: rollout, certificate Ready, Gateway Programmed
               → verify over HTTPS: trusted cert, TLS ≥1.2, security headers,
                 HTTP→HTTPS redirect, untrusted cert rejected, health checker UP
```

Each run's summary page shows the live pods, the certificate, the response headers and the cow.

## Problem Statement 1: containerise and deploy

| Requirement | Where |
|---|---|
| Dockerfile | [`Dockerfile`](Dockerfile) |
| Kubernetes manifests, app exposed as a Service | [`k8s/`](k8s) (Kustomize): Namespace, Deployment, Service |
| CI: build and push image on every commit | [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml), job `build` |
| **Challenge:** continuous deployment | job `deploy`: deploys the exact image just built (`sha-<commit>`) and tests it |
| **Challenge:** TLS | [`k8s/tls.yaml`](k8s/tls.yaml) (cert-manager) + [`k8s/gateway.yaml`](k8s/gateway.yaml) (Gateway API, HTTPS listener, HTTP→HTTPS redirect, HSTS) |

### Design choices

- **Gateway API instead of Ingress.** Gateway API is the current Kubernetes standard for traffic
  routing, and the community ingress-nginx controller has been retired. The manifests work with any
  conformant controller; CI uses Envoy Gateway.
- **cert-manager issues and renews the certificate** (ECDSA P-256, 90 days, renewed 15 days early,
  key rotated on renewal). It is self-signed so it works on any cluster; for a public domain, swap
  the `Issuer` for an ACME (Let's Encrypt) one and nothing else changes.
- **Locked-down pods.** The namespace enforces the `restricted` Pod Security Standard. Containers
  run as UID 10001 with a read-only root filesystem, all Linux capabilities dropped, no privilege
  escalation, the RuntimeDefault seccomp profile and no service-account token. The only writable
  path is a 1 MiB in-memory `/tmp` that holds the named pipe.
- **Health checks.** `/healthz` backs the readiness and liveness probes.
- **App hardening** ([`wisecow.sh`](wisecow.sh)). Valid HTML5 page with light/dark support,
  fortune text HTML-escaped, a correct byte-accurate `Content-Length`, and security headers:
  a strict Content-Security-Policy (no scripts; the inline CSS is allowed by its SHA-256 hash,
  checked by a test), `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`.
- **Supply chain.** Every GitHub Action is pinned to a full commit SHA, workflow permissions are
  read-only by default, pull requests never push images, and images are scanned before they are
  pushed.

### Run it yourself

```bash
# Local container
docker build -t wisecow . && docker run --rm -p 4499:4499 --read-only --tmpfs /tmp wisecow
curl localhost:4499

# Any Kubernetes cluster with cert-manager and a Gateway API controller (GatewayClass "eg")
kubectl apply -k k8s
kubectl -n wisecow get secret wisecow-tls -o jsonpath='{.data.ca\.crt}' | base64 -d > ca.crt
curl --cacert ca.crt https://wisecow.local/   # point wisecow.local at your Gateway's address
```

The exact cluster setup used in CI (versions included) is in the `deploy` job.

## Problem Statement 2: scripts (Python, standard library only)

**1. System health monitor**: [`scripts/sys_health.py`](scripts/sys_health.py)
Reads `/proc` for CPU (sampled over time, not a single snapshot), memory (`MemAvailable`, so the
page cache is not counted as used), disk usage and process count. Every breach is logged as an
`ALERT` to the console and optionally a log file. Exit code 1 on any alert, so cron or CI can act on it.

```bash
python3 scripts/sys_health.py --cpu 80 --mem 80 --disk 90 --procs 500 --log health.log
python3 scripts/sys_health.py --interval 60        # keep monitoring
```

**4. Application health checker**: [`scripts/app_health.py`](scripts/app_health.py)
Reports **UP** for HTTP 2xx/3xx and **DOWN** for 4xx/5xx, timeouts, refused connections, and DNS or
TLS errors. It retries with backoff before declaring DOWN, does not follow redirects (a redirect means
the app is answering), and shows the response time. Exit code 1 if any URL is DOWN.

```bash
python3 scripts/app_health.py https://example.com https://wisecow.local --cafile ca.crt
python3 scripts/app_health.py https://example.com --interval 30
```

## Tests

`uvx pytest` runs 18 tests: CPU, memory and process parsing against fixture `/proc` files, threshold
boundaries, UP/DOWN for real HTTP status codes from a local test server, retries on refused
connections, exit codes, HTML escaping, byte-accurate `Content-Length` with Unicode, and the CSP hash.

Full test plan (35 cases, with which ones CI runs): [`docs/TEST_CASES.md`](docs/TEST_CASES.md),
also as [`docs/test-cases.csv`](docs/test-cases.csv).

## Layout

```
wisecow.sh              the app
Dockerfile
k8s/                    namespace, deployment, service, tls (cert-manager), gateway (Gateway API)
ci/gatewayclass.yaml    cluster-level controller binding used by CI
.github/workflows/      CI/CD pipeline
scripts/                Problem Statement 2
tests/                  pytest
docs/                   test cases
```

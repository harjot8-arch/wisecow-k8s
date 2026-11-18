# Test cases

All 35 cases run automatically on each push in `.github/workflows/ci-cd.yml`.
A spreadsheet version is in [`test-cases.csv`](test-cases.csv) (import into Google Sheets).

| ID | Area | Test case | Steps | Expected result | Type | How |
|---|---|---|---|---|---|---|
| TC-01 | Container | Image builds | `docker build .` | Build succeeds | Functional | CI |
| TC-02 | Container | App answers inside the container | Run image, `GET /` | `200`, HTML page with `<pre>` cow | Functional | CI |
| TC-03 | Container | Health endpoint | `GET /healthz` | `200 ok` | Functional | CI |
| TC-04 | Container | Runs as non-root | `docker exec … id -u` | `10001` | Security | CI |
| TC-05 | Container | Works with read-only filesystem and no Linux capabilities | `docker run --read-only --tmpfs /tmp --cap-drop ALL` | App still serves | Security | CI |
| TC-06 | Container | No fixable critical vulnerabilities | Grype scan | No fixable critical CVEs | Security | CI |
| TC-07 | Container | Dockerfile best practices | Hadolint | No warnings | Static | CI |
| TC-08 | App | Fortune text is HTML-escaped | Fortune containing `<b>&</b>` | Rendered as `&lt;b&gt;&amp;&lt;/b&gt;` | Security | CI |
| TC-09 | App | Content-Length matches body bytes, incl. Unicode | Compare header to body | Equal | Functional | CI |
| TC-10 | App | CSP hash matches inline CSS | `pytest tests/test_wisecow_page.py` | Hashes equal | Security | CI |
| TC-11 | App | Shell script quality | ShellCheck | No findings | Static | CI |
| TC-12 | Kubernetes | Manifests are valid | kubeconform, strict | All resources valid | Static | CI |
| TC-13 | Kubernetes | Deployment rolls out | `kubectl rollout status` | 2/2 pods ready | Functional | CI |
| TC-14 | Kubernetes | Namespace enforces restricted Pod Security | Apply manifests | Pods admitted (proves they meet `restricted`) | Security | CI |
| TC-15 | Kubernetes | Pod self-heals | Delete a pod | Replacement Ready, 2/2 replicas within 60 s | Reliability | CI |
| TC-16 | Kubernetes | Liveness probe restarts a hung app | Freeze the `nc` listener (SIGSTOP) so the app stops answering | Container restarted (restartCount 1), Ready again | Reliability | CI |
| TC-17 | TLS | Certificate issued | `kubectl wait certificate --for=Ready` | Ready | Functional | CI |
| TC-18 | TLS | HTTPS works with the trusted CA | `curl --cacert ca.crt https://wisecow.local` | `200`, cow page | Functional | CI |
| TC-19 | TLS | Untrusted certificate rejected | `curl` without the CA | TLS verification error | Security | CI |
| TC-20 | TLS | Modern TLS accepted, old TLS refused | `curl --tlsv1.2`; `openssl s_client -tls1_3` and `-tls1_1` (client allows weak, so only the server can refuse) | 1.2 and 1.3 work; 1.1 refused | Security | CI |
| TC-21 | TLS | HTTP redirects to HTTPS | `GET http://wisecow.local` | `301` to `https://` | Security | CI |
| TC-22 | TLS | Security headers present | Inspect HTTPS response | HSTS, CSP, nosniff, X-Frame-Options | Security | CI |
| TC-23 | CI/CD | Image pushed to registry | Push to `main` | `ghcr.io/harjot8-arch/wisecow:sha-<commit>` and `:latest` exist | Functional | CI |
| TC-24 | CI/CD | Deploy uses the exact image just built | Check pod image | Tag equals `sha-<commit>` | Functional | CI |
| TC-25 | CI/CD | Pull requests do not push images | Open a PR | Pipeline runs; no push | Functional | CI |
| TC-26 | sys_health | CPU % from two `/proc/stat` samples | Unit test | 66.67 % for the fixture | Functional | CI |
| TC-27 | sys_health | Memory uses MemAvailable, not MemFree | Unit test | 75 % for the fixture | Functional | CI |
| TC-28 | sys_health | Threshold is strictly greater-than | 80 vs limit 80 | Not breached | Boundary | CI |
| TC-29 | sys_health | Alert logged and exit code 1 on breach | Limit below current value | `ALERT …`, exit 1 | Functional | CI |
| TC-30 | sys_health | Only numeric `/proc` entries counted as processes | Fixture with `self` dir | Count = 3 | Functional | CI |
| TC-31 | app_health | 2xx and 3xx are UP | 200, 204, 301 | UP | Functional | CI |
| TC-32 | app_health | 4xx and 5xx are DOWN | 404, 500, 503 | DOWN with the code | Functional | CI |
| TC-33 | app_health | Connection refused is DOWN after retries | Closed port | DOWN, error named | Negative | CI |
| TC-34 | app_health | Exit code reflects the worst result | One UP + one DOWN | Exit 1 | Functional | CI |
| TC-35 | app_health | Works against the deployed HTTPS app | Run with `--cafile` | UP | Integration | CI |

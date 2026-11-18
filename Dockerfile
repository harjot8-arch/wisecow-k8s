# syntax=docker/dockerfile:1
FROM debian:bookworm-slim

# What wisecow.sh needs: fortune (quotes), cowsay (the cow), netcat-openbsd (`nc -lN`).
RUN apt-get update \
 && apt-get install -y --no-install-recommends fortune-mod fortunes-min cowsay netcat-openbsd \
 && rm -rf /var/lib/apt/lists/*

# Debian installs fortune and cowsay into /usr/games, which is not on PATH by default.
ENV PATH="/usr/games:${PATH}" \
    SRVPORT=4499 \
    RSPFILE=/tmp/wisecow-response

COPY --chmod=0555 wisecow.sh /app/wisecow.sh

# Never run as root. The UID matches runAsUser in k8s/deployment.yaml.
USER 10001:10001
EXPOSE 4499
ENTRYPOINT ["/app/wisecow.sh"]

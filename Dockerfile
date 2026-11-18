# Small, well-known base image.
FROM debian:bookworm-slim

# The three tools wisecow.sh needs:
#   fortune-mod + fortunes-min -> random quotes
#   cowsay                     -> draws the cow
#   netcat-openbsd             -> tiny TCP server (supports `nc -lN`)
RUN apt-get update \
 && apt-get install -y --no-install-recommends fortune-mod fortunes-min cowsay netcat-openbsd \
 && rm -rf /var/lib/apt/lists/*

# Debian installs fortune and cowsay in /usr/games, which is not on PATH by default.
ENV PATH="/usr/games:${PATH}"

# Run as a normal user, not root (least privilege).
RUN useradd --create-home --uid 10001 wisecow
WORKDIR /app
COPY --chown=wisecow:wisecow wisecow.sh .
RUN chmod +x wisecow.sh
USER 10001

EXPOSE 4499
CMD ["./wisecow.sh"]

#!/usr/bin/env bash
# Wisecow: serves a random fortune, said by a cow, over HTTP.
# One request at a time, using netcat and a named pipe.
set -u

SRVPORT="${SRVPORT:-4499}"
# The pipe lives in /tmp so the container's root filesystem can stay read-only.
RSPFILE="${RSPFILE:-/tmp/wisecow-response}"

# Inline CSS. Its SHA-256 is pinned in the Content-Security-Policy below;
# tests/test_wisecow_page.py fails if the two ever drift apart.
STYLE=':root{color-scheme:light dark}body{margin:0;min-block-size:100dvh;display:grid;place-items:center;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}pre{margin:1rem;max-inline-size:100%;overflow-x:auto}'
CSP="default-src 'none'; style-src 'sha256-MmbxSRBrqGzTvpUf5CWKsna7RTV3jSzZcWR6Dgz/RkQ='; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"

html_escape() {
	sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

page() {
	local cow
	cow="$(fortune | cowsay | html_escape)"
	cat <<EOF
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Wisecow</title>
<style>${STYLE}</style>
</head>
<body>
<main><pre>${cow}</pre></main>
</body>
</html>
EOF
}

# respond STATUS CONTENT_TYPE BODY
respond() {
	local LC_ALL=C # so ${#3} counts bytes, not characters
	printf 'HTTP/1.1 %s\r\n' "$1"
	printf 'Content-Type: %s\r\n' "$2"
	printf 'Content-Length: %d\r\n' "${#3}"
	printf 'Content-Security-Policy: %s\r\n' "$CSP"
	printf 'X-Content-Type-Options: nosniff\r\n'
	printf 'X-Frame-Options: DENY\r\n'
	printf 'Referrer-Policy: no-referrer\r\n'
	printf 'Cache-Control: no-store\r\n'
	printf 'Connection: close\r\n\r\n'
	printf '%s' "$3"
}

handleRequest() {
	local method path _
	read -r method path _ || true
	path="${path%$'\r'}"
	echo "${method:-?} ${path:-?}" >&2

	case "$path" in
	/healthz) respond '200 OK' 'text/plain; charset=utf-8' 'ok' ;;
	*) respond '200 OK' 'text/html; charset=utf-8' "$(page)" ;;
	esac >"$RSPFILE"
}

prerequisites() {
	command -v cowsay >/dev/null 2>&1 &&
		command -v fortune >/dev/null 2>&1 &&
		command -v nc >/dev/null 2>&1 || {
		echo "Install prerequisites: fortune-mod cowsay netcat-openbsd" >&2
		exit 1
	}
}

main() {
	prerequisites
	rm -f "$RSPFILE"
	mkfifo "$RSPFILE"
	trap 'rm -f "$RSPFILE"; exit 0' INT TERM
	echo "Wisdom served on port=$SRVPORT..."

	while true; do
		# cat (not "<") so the pipe is opened only after nc is already listening.
		# shellcheck disable=SC2002
		cat "$RSPFILE" | nc -lN "$SRVPORT" | handleRequest
	done
}

main

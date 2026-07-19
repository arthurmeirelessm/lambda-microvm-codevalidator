#!/usr/bin/env bash
set -euo pipefail

mkdir -p /var/lib/docker /var/run /var/log

if command -v dockerd >/dev/null 2>&1; then
  dockerd \
    --host=unix:///var/run/docker.sock \
    --data-root=/var/lib/docker \
    --exec-root=/var/run/docker \
    --storage-driver=vfs \
    --iptables=false \
    --ip-masq=false \
    --bridge=none \
    >/var/log/dockerd.log 2>&1 &
fi

exec python3 /app/app.py

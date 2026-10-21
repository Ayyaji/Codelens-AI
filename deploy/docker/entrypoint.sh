#!/bin/sh
# Refuse to start when the persistent directories are not writable.
# The image runs as uid 10001 (codelens). deploy/ec2/bootstrap.sh chowns the
# host directories to that uid before the first boot.
set -eu

if [ ! -w /data/chroma ] || [ ! -w /cache/huggingface ]; then
    echo "CodeLens cannot write /data/chroma or /cache/huggingface (uid $(id -u))." >&2
    echo "On the host, run: sudo chown -R 10001:10001 /opt/codelens/data /opt/codelens/cache" >&2
    exit 1
fi

exec "$@"

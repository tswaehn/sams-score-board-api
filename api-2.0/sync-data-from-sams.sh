#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <ssh-host>" >&2
  exit 64
fi

REMOTE_HOST=$1

# Resolve the destination relative to this script so it can be run from any directory.
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

mkdir -p "$SCRIPT_DIR/data"
exec rsync -av "$REMOTE_HOST:/docker/sams-2.0/data/" "$SCRIPT_DIR/data/"

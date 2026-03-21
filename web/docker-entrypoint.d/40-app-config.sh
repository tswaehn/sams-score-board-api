#!/bin/sh
set -eu

API_BASE_URL="${API_BASE_URL:-http://localhost:8000/api}"
LIVE_API_URL="${LIVE_API_URL:-http://localhost:9000/live}"

cat > /usr/share/nginx/html/app-config.js <<EOF
window.__APP_CONFIG__ = {
  apiBaseUrl: "${API_BASE_URL}",
  liveApiUrl: "${LIVE_API_URL}"
};
EOF

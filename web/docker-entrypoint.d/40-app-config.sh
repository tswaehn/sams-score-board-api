#!/bin/sh
set -eu

API_BASE_URL="${API_BASE_URL:-http://localhost:8000/api}"

cat > /usr/share/nginx/html/app-config.js <<EOF
window.__APP_CONFIG__ = {
  apiBaseUrl: "${API_BASE_URL}"
};
EOF

#!/usr/bin/env bash
# S3 + CloudFront alternative. The primary frontend is the EC2 Nginx host
# (deploy/frontend/deploy.sh), which bakes VITE_API_URL=/api.
# Use this script only when the static site is hosted on S3. VITE_API_URL
# must then be the public HTTPS origin of the API, and CORS_ORIGINS on the
# backend must list the CloudFront site.
#
# Build the React app and upload it to the private S3 bucket behind CloudFront.
#
# Required environment:
#   VITE_API_URL                 Public API origin, no trailing slash
#   S3_BUCKET                    Frontend bucket name
# Optional:
#   AWS_REGION                   Default ap-south-1
#   CLOUDFRONT_DISTRIBUTION_ID   Invalidates the distribution after upload
#
# The API origin is baked into the static files. Changing it means running
# this script again. CORS on the API must allow the CloudFront site that
# serves these files.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AWS_REGION="${AWS_REGION:-ap-south-1}"

: "${VITE_API_URL:?Set VITE_API_URL to the public API origin, with no trailing slash}"
: "${S3_BUCKET:?Set S3_BUCKET to the frontend bucket name}"

VITE_API_URL="${VITE_API_URL%/}"
case "$VITE_API_URL" in
  https://*)
    ;;
  http://localhost*|http://127.0.0.1*)
    echo "Refusing to upload a build whose API is ${VITE_API_URL}." >&2
    echo "Set VITE_API_URL to the HTTPS API origin." >&2
    exit 1
    ;;
  http://*)
    echo "VITE_API_URL is plain HTTP (${VITE_API_URL})." >&2
    echo "The CloudFront site is HTTPS, and the browser will block these calls." >&2
    echo "Use the API CloudFront URL, or https://api.yourdomain." >&2
    exit 1
    ;;
  *)
    echo "VITE_API_URL must start with https://." >&2
    exit 1
    ;;
esac

command -v npm >/dev/null 2>&1 || {
  echo "npm is not installed." >&2
  exit 1
}
command -v aws >/dev/null 2>&1 || {
  echo "The AWS CLI is not installed." >&2
  exit 1
}

cd "${ROOT}/frontend"
npm ci
VITE_API_URL="$VITE_API_URL" \
  VITE_USE_MOCKS=false \
  VITE_MOCK_ENDPOINTS= \
  npm run build

test -f dist/index.html

aws s3 sync dist/ "s3://${S3_BUCKET}/" \
  --region "$AWS_REGION" \
  --delete \
  --cache-control "public,max-age=31536000,immutable" \
  --exclude "index.html" \
  --exclude "*.map" \
  --exclude ".DS_Store"

aws s3 cp dist/index.html "s3://${S3_BUCKET}/index.html" \
  --region "$AWS_REGION" \
  --cache-control "no-cache,no-store,must-revalidate" \
  --content-type "text/html; charset=utf-8"

if [[ -n "${CLOUDFRONT_DISTRIBUTION_ID:-}" ]]; then
  aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --paths "/*" >/dev/null
  echo "Invalidated CloudFront distribution ${CLOUDFRONT_DISTRIBUTION_ID}."
fi

echo "Uploaded to s3://${S3_BUCKET}/ with API ${VITE_API_URL}."

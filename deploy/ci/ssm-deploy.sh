#!/usr/bin/env bash
# Send one deploy command to an instance. Used by the GitHub Actions workflow.
#   INSTANCE_ID=i-... DEPLOY_REF=cursor/mongodb-auth-backend-3267 bash deploy/ci/ssm-deploy.sh backend
set -euo pipefail

target="${1:-}"
instance="${INSTANCE_ID:-}"
ref="${DEPLOY_REF:-}"
region="${AWS_REGION:-ap-south-1}"

case "$target" in
  frontend) script="bash deploy/frontend/deploy.sh" ;;
  backend) script="bash deploy/backend/deploy.sh" ;;
  *)
    echo "Usage: ssm-deploy.sh frontend|backend" >&2
    exit 1
    ;;
esac
if [[ ! "$instance" =~ ^i-[0-9a-f]+$ ]]; then
  echo "Set INSTANCE_ID to an EC2 instance id." >&2
  exit 1
fi
if [[ ! "$ref" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  echo "Set DEPLOY_REF to the git branch that should be deployed." >&2
  exit 1
fi

params="$(jq -n --arg ref "$ref" --arg script "$script" '{
  commands: [
    "set -euo pipefail",
    "cd /opt/codelens/app",
    "git config --global --add safe.directory /opt/codelens/app",
    ("git fetch origin " + $ref),
    ("git checkout " + $ref),
    ("git pull --ff-only origin " + $ref),
    $script
  ]
}')"

command_id="$(aws ssm send-command \
  --region "$region" \
  --instance-ids "$instance" \
  --document-name AWS-RunShellScript \
  --comment "CodeLens ${target} deploy" \
  --parameters "$params" \
  --query Command.CommandId --output text)"

echo "SSM command ${command_id} on ${instance}"
for _ in $(seq 1 60); do
  status="$(aws ssm get-command-invocation \
    --region "$region" \
    --command-id "$command_id" \
    --instance-id "$instance" \
    --query Status --output text 2>/dev/null || echo Pending)"
  case "$status" in
    Success)
      aws ssm get-command-invocation --region "$region" \
        --command-id "$command_id" --instance-id "$instance" \
        --query StandardOutputContent --output text
      exit 0
      ;;
    Failed|Cancelled|TimedOut|DeliveryTimedOut)
      echo "SSM command ${status}" >&2
      aws ssm get-command-invocation --region "$region" \
        --command-id "$command_id" --instance-id "$instance" \
        --query StandardErrorContent --output text >&2 || true
      exit 1
      ;;
  esac
  sleep 10
done
echo "Timed out waiting for ${command_id}" >&2
exit 1

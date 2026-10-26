#!/usr/bin/env bash
# Tag the MongoDB data volume and create a daily DLM snapshot policy.
# Run from the laptop, with the AWS CLI pointed at ap-south-1.
#
#   VOLUME_ID=vol-0123456789abcdef0 bash deploy/mongo/setup-snapshots.sh
#
# Snapshots are taken at 18:30 UTC, which is midnight in India, and 7 are kept.
# DLM has no charge of its own. You pay for the snapshot storage.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_REGION="${AWS_REGION:-ap-south-1}"
VOLUME_ID="${VOLUME_ID:-}"

if [[ ! "$VOLUME_ID" =~ ^vol-[0-9a-f]+$ ]]; then
  echo "Set VOLUME_ID to the 20 GB data volume, for example vol-0123456789abcdef0." >&2
  exit 1
fi

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ROLE_NAME="${DLM_ROLE_NAME:-codelens-dlm}"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

aws ec2 create-tags --region "$AWS_REGION" \
  --resources "$VOLUME_ID" \
  --tags Key=Project,Value=codelens Key=Role,Value=mongo-data Key=Name,Value=codelens-mongo-data

if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "file://${ROOT_DIR}/../iam/dlm-trust.json" \
    --description "CodeLens Data Lifecycle Manager snapshots"
  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole
  echo "Waiting for the new role to become usable..."
  sleep 10
fi

POLICY_FILE="$(mktemp)"
cat >"$POLICY_FILE" <<'EOF'
{
  "PolicyType": "EBS_SNAPSHOT_MANAGEMENT",
  "ResourceTypes": ["VOLUME"],
  "TargetTags": [
    {"Key": "Project", "Value": "codelens"},
    {"Key": "Role", "Value": "mongo-data"}
  ],
  "Schedules": [
    {
      "Name": "daily-midnight-ist",
      "CreateRule": {"Interval": 24, "IntervalUnit": "HOURS", "Times": ["18:30"]},
      "RetainRule": {"Count": 7},
      "CopyTags": true,
      "TagsToAdd": [{"Key": "Project", "Value": "codelens"}]
    }
  ]
}
EOF

existing="$(aws dlm get-lifecycle-policies --region "$AWS_REGION" \
  --query "Policies[?Description=='CodeLens MongoDB daily snapshots'].PolicyId | [0]" \
  --output text 2>/dev/null || true)"
if [[ -n "$existing" && "$existing" != "None" ]]; then
  echo "DLM policy already exists: ${existing}"
else
  policy_id="$(aws dlm create-lifecycle-policy --region "$AWS_REGION" \
    --description "CodeLens MongoDB daily snapshots" \
    --state ENABLED \
    --execution-role-arn "$ROLE_ARN" \
    --policy-details "file://${POLICY_FILE}" \
    --query PolicyId --output text)"
  echo "Created DLM policy ${policy_id}"
fi
rm -f "$POLICY_FILE"
echo "Volume ${VOLUME_ID} is tagged Role=mongo-data. The next snapshot is at 18:30 UTC."

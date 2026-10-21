#!/usr/bin/env bash
# Create the EC2 instance role used by all three servers.
# Run once from the laptop after aws configure.
#   bash deploy/iam/setup-roles.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROLE_NAME=codelens-ec2
PROFILE_NAME=codelens-ec2

if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document "file://${ROOT_DIR}/ec2-trust.json" \
    --description "CodeLens EC2 instances: Session Manager and SSM parameters"
fi

aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name codelens-ssm-params \
  --policy-document "file://${ROOT_DIR}/instance-ssm-params.json"

if ! aws iam get-instance-profile --instance-profile-name "$PROFILE_NAME" >/dev/null 2>&1; then
  aws iam create-instance-profile --instance-profile-name "$PROFILE_NAME"
fi

attached="$(aws iam list-instance-profiles-for-role --role-name "$ROLE_NAME" \
  --query "InstanceProfiles[?InstanceProfileName=='${PROFILE_NAME}'] | length(@)" --output text)"
if [[ "$attached" == "0" ]]; then
  aws iam add-role-to-instance-profile \
    --instance-profile-name "$PROFILE_NAME" \
    --role-name "$ROLE_NAME"
fi

echo "Instance profile ${PROFILE_NAME} is ready. Select it when you launch each instance."
echo "New instance profiles can take a minute to appear in the EC2 launch screen."

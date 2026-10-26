#!/usr/bin/env bash
# Delete the VPC created by setup-network.sh. Instances must already be terminated.
#   CONFIRM=delete bash deploy/vpc/teardown-network.sh
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"

if [[ "${CONFIRM:-}" != "delete" ]]; then
  echo "This deletes the codelens VPC, subnets, security groups, and NAT gateway if one exists." >&2
  echo "Re-run with CONFIRM=delete after the three instances are terminated." >&2
  exit 1
fi

vpc_id="$(aws ec2 describe-vpcs \
  --filters Name=tag:Name,Values=codelens Name=tag:Project,Values=codelens \
  --query 'Vpcs[0].VpcId' --output text)"
if [[ -z "$vpc_id" || "$vpc_id" == "None" ]]; then
  echo "No codelens VPC in ${AWS_REGION}."
  exit 0
fi

instances="$(aws ec2 describe-instances \
  --filters Name=vpc-id,Values="$vpc_id" Name=instance-state-name,Values=pending,running,stopping,stopped \
  --query 'Reservations[].Instances[].InstanceId' --output text)"
if [[ -n "$instances" && "$instances" != "None" ]]; then
  echo "Terminate these instances first: ${instances}" >&2
  exit 1
fi

nats="$(aws ec2 describe-nat-gateways \
  --filter Name=vpc-id,Values="$vpc_id" Name=state,Values=available,pending \
  --query 'NatGateways[].NatGatewayId' --output text)"
if [[ -n "$nats" && "$nats" != "None" ]]; then
  for nat in $nats; do
    alloc="$(aws ec2 describe-nat-gateways --nat-gateway-ids "$nat" \
      --query 'NatGateways[0].NatGatewayAddresses[0].AllocationId' --output text)"
    aws ec2 delete-nat-gateway --nat-gateway-id "$nat" >/dev/null
    aws ec2 wait nat-gateway-deleted --nat-gateway-ids "$nat"
    if [[ -n "$alloc" && "$alloc" != "None" ]]; then
      aws ec2 release-address --allocation-id "$alloc" || true
    fi
  done
fi

igws="$(aws ec2 describe-internet-gateways \
  --filters Name=attachment.vpc-id,Values="$vpc_id" \
  --query 'InternetGateways[].InternetGatewayId' --output text)"
for igw in $igws; do
  [[ "$igw" == "None" || -z "$igw" ]] && continue
  aws ec2 detach-internet-gateway --internet-gateway-id "$igw" --vpc-id "$vpc_id" || true
  aws ec2 delete-internet-gateway --internet-gateway-id "$igw" || true
done

subs="$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$vpc_id" --query 'Subnets[].SubnetId' --output text)"
for subnet in $subs; do
  [[ "$subnet" == "None" || -z "$subnet" ]] && continue
  aws ec2 delete-subnet --subnet-id "$subnet" || true
done

rts="$(aws ec2 describe-route-tables --filters Name=vpc-id,Values="$vpc_id" \
  --query 'RouteTables[?Associations[0].Main!=`true`].RouteTableId' --output text)"
for rt in $rts; do
  [[ "$rt" == "None" || -z "$rt" ]] && continue
  assoc="$(aws ec2 describe-route-tables --route-table-ids "$rt" \
    --query 'RouteTables[0].Associations[?Main!=`true`].RouteTableAssociationId' --output text)"
  for id in $assoc; do
    [[ "$id" == "None" || -z "$id" ]] && continue
    aws ec2 disassociate-route-table --association-id "$id" || true
  done
  aws ec2 delete-route-table --route-table-id "$rt" || true
done

sgs="$(aws ec2 describe-security-groups --filters Name=vpc-id,Values="$vpc_id" \
  --query 'SecurityGroups[?GroupName!=`default`].GroupId' --output text)"
for sg in $sgs; do
  [[ "$sg" == "None" || -z "$sg" ]] && continue
  aws ec2 delete-security-group --group-id "$sg" || true
done

aws ec2 delete-vpc --vpc-id "$vpc_id"
echo "Deleted VPC ${vpc_id}."

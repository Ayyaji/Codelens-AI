#!/usr/bin/env bash
# Create the CodeLens VPC in ap-south-1.
# One public subnet and one private subnet, in the same AZ, plus three
# security groups. A NAT gateway is created only when WITH_NAT=1.
#
#   ADMIN_CIDR="$(curl -fsS https://checkip.amazonaws.com)/32" bash deploy/vpc/setup-network.sh
#
# Prints the ids and writes them to ./codelens-network.txt. Re-running prints
# the existing VPC instead of creating a second one.
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
AZ="${CODELENS_AZ:-ap-south-1a}"
ADMIN_CIDR="${ADMIN_CIDR:-}"
WITH_NAT="${WITH_NAT:-0}"
SKIP_SSH="${SKIP_SSH:-0}"
KEY_NAME="${KEY_NAME:-codelens-key}"
OUT="${CODELENS_NETWORK_OUT:-codelens-network.txt}"

if [[ "$SKIP_SSH" != "1" ]]; then
  if [[ ! "$ADMIN_CIDR" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+$ ]]; then
    echo "Set ADMIN_CIDR to your public IP with a /32 suffix." >&2
    echo "Example: ADMIN_CIDR=\$(curl -fsS https://checkip.amazonaws.com)/32" >&2
    exit 1
  fi
fi

export AWS_DEFAULT_REGION="$AWS_REGION"

vpc_id="$(aws ec2 describe-vpcs \
  --filters Name=tag:Name,Values=codelens Name=tag:Project,Values=codelens \
  --query 'Vpcs[0].VpcId' --output text)"
if [[ -n "$vpc_id" && "$vpc_id" != "None" ]]; then
  echo "VPC codelens already exists (${vpc_id}). Nothing new was created."
  aws ec2 describe-subnets --filters Name=vpc-id,Values="$vpc_id" \
    --query 'Subnets[].{id:SubnetId,name:Tags[?Key==`Name`].Value|[0],cidr:CidrBlock,az:AvailabilityZone}' \
    --output table
  aws ec2 describe-security-groups --filters Name=vpc-id,Values="$vpc_id" \
    --query 'SecurityGroups[].{id:GroupId,name:GroupName}' --output table
  exit 0
fi

echo "Creating VPC 10.0.0.0/16 in ${AWS_REGION} (${AZ})..."
vpc_id="$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=codelens},{Key=Project,Value=codelens}]' \
  --query Vpc.Id --output text)"
aws ec2 modify-vpc-attribute --vpc-id "$vpc_id" --enable-dns-support '{"Value":true}'
aws ec2 modify-vpc-attribute --vpc-id "$vpc_id" --enable-dns-hostnames '{"Value":true}'

igw_id="$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=codelens},{Key=Project,Value=codelens}]' \
  --query InternetGateway.InternetGatewayId --output text)"
aws ec2 attach-internet-gateway --internet-gateway-id "$igw_id" --vpc-id "$vpc_id"

pub_id="$(aws ec2 create-subnet --vpc-id "$vpc_id" --cidr-block 10.0.1.0/24 --availability-zone "$AZ" \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=codelens-public},{Key=Project,Value=codelens}]' \
  --query Subnet.SubnetId --output text)"
priv_id="$(aws ec2 create-subnet --vpc-id "$vpc_id" --cidr-block 10.0.2.0/24 --availability-zone "$AZ" \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=codelens-private},{Key=Project,Value=codelens}]' \
  --query Subnet.SubnetId --output text)"
aws ec2 modify-subnet-attribute --subnet-id "$pub_id" --map-public-ip-on-launch '{"Value":true}'

pub_rt="$(aws ec2 create-route-table --vpc-id "$vpc_id" \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=codelens-public},{Key=Project,Value=codelens}]' \
  --query RouteTable.RouteTableId --output text)"
aws ec2 create-route --route-table-id "$pub_rt" --destination-cidr-block 0.0.0.0/0 --gateway-id "$igw_id" >/dev/null
aws ec2 associate-route-table --route-table-id "$pub_rt" --subnet-id "$pub_id" >/dev/null

priv_rt="$(aws ec2 create-route-table --vpc-id "$vpc_id" \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=codelens-private},{Key=Project,Value=codelens}]' \
  --query RouteTable.RouteTableId --output text)"
aws ec2 associate-route-table --route-table-id "$priv_rt" --subnet-id "$priv_id" >/dev/null

nat_id="none"
if [[ "$WITH_NAT" == "1" ]]; then
  echo "Creating a NAT gateway. This costs about \$0.045 an hour plus data, about \$33 a month before data."
  alloc="$(aws ec2 allocate-address --domain vpc \
    --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=codelens-nat},{Key=Project,Value=codelens}]' \
    --query AllocationId --output text)"
  nat_id="$(aws ec2 create-nat-gateway --subnet-id "$pub_id" --allocation-id "$alloc" \
    --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=codelens},{Key=Project,Value=codelens}]' \
    --query NatGateway.NatGatewayId --output text)"
  aws ec2 wait nat-gateway-available --nat-gateway-ids "$nat_id"
  aws ec2 create-route --route-table-id "$priv_rt" --destination-cidr-block 0.0.0.0/0 --nat-gateway-id "$nat_id" >/dev/null
else
  echo "No NAT gateway. The private subnet has no route to the internet."
  echo "Install MongoDB while that instance is still in the public subnet, then move it. See docs/DEPLOY_AWS.md."
fi

fe="$(aws ec2 create-security-group --vpc-id "$vpc_id" --group-name codelens-frontend \
  --description "CodeLens frontend Nginx" --query GroupId --output text)"
be="$(aws ec2 create-security-group --vpc-id "$vpc_id" --group-name codelens-backend \
  --description "CodeLens API" --query GroupId --output text)"
db="$(aws ec2 create-security-group --vpc-id "$vpc_id" --group-name codelens-mongo \
  --description "CodeLens MongoDB" --query GroupId --output text)"
aws ec2 create-tags --resources "$fe" "$be" "$db" --tags Key=Project,Value=codelens

aws ec2 authorize-security-group-ingress --group-id "$fe" --protocol tcp --port 80 --cidr 0.0.0.0/0 >/dev/null
aws ec2 authorize-security-group-ingress --group-id "$fe" --protocol tcp --port 443 --cidr 0.0.0.0/0 >/dev/null
aws ec2 authorize-security-group-ingress --group-id "$be" --protocol tcp --port 8000 --source-group "$fe" >/dev/null
aws ec2 authorize-security-group-ingress --group-id "$be" --protocol tcp --port 22 --source-group "$fe" >/dev/null
aws ec2 authorize-security-group-ingress --group-id "$db" --protocol tcp --port 27017 --source-group "$be" >/dev/null
aws ec2 authorize-security-group-ingress --group-id "$db" --protocol tcp --port 22 --source-group "$fe" >/dev/null
if [[ "$SKIP_SSH" != "1" ]]; then
  aws ec2 authorize-security-group-ingress --group-id "$fe" --protocol tcp --port 22 --cidr "$ADMIN_CIDR" >/dev/null
  aws ec2 authorize-security-group-ingress --group-id "$be" --protocol tcp --port 22 --cidr "$ADMIN_CIDR" >/dev/null
fi

if aws ec2 describe-key-pairs --key-names "$KEY_NAME" >/dev/null 2>&1; then
  echo "Key pair ${KEY_NAME} already exists in AWS. The .pem file is not re-downloaded."
else
  umask 077
  aws ec2 create-key-pair --key-name "$KEY_NAME" \
    --tag-specifications 'ResourceType=key-pair,Tags=[{Key=Name,Value=codelens},{Key=Project,Value=codelens}]' \
    --query KeyMaterial --output text >"${KEY_NAME}.pem"
  chmod 400 "${KEY_NAME}.pem"
  echo "Wrote ${KEY_NAME}.pem in the current directory. Keep it private. It is not committed."
fi

cat >"$OUT" <<EOF
region=${AWS_REGION}
az=${AZ}
vpc_id=${vpc_id}
internet_gateway_id=${igw_id}
public_subnet_id=${pub_id}
private_subnet_id=${priv_id}
public_route_table_id=${pub_rt}
private_route_table_id=${priv_rt}
nat_gateway_id=${nat_id}
frontend_sg_id=${fe}
backend_sg_id=${be}
mongo_sg_id=${db}
key_name=${KEY_NAME}
admin_cidr=${ADMIN_CIDR:-none}
EOF
echo "Wrote ${OUT}"
cat "$OUT"

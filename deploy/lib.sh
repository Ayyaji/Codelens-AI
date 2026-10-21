# Shared helpers for the deploy scripts. Source this file; do not execute it.
set -euo pipefail

app_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd
}

require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this script with sudo." >&2
    exit 1
  fi
}

upsert_env() {
  local key="$1"
  local value="$2"
  local file="$3"
  local escaped="${value//\'/\'\\\'\'}"
  local line="${key}='${escaped}'"
  local tmp
  mkdir -p "$(dirname "$file")"
  touch "$file"
  tmp="$(mktemp)"
  grep -v "^${key}=" "$file" >"$tmp" || true
  printf '%s\n' "$line" >>"$tmp"
  mv "$tmp" "$file"
  chmod 600 "$file"
}

read_ssm() {
  local name="$1"
  aws ssm get-parameter \
    --name "$name" \
    --with-decryption \
    --region "${AWS_REGION:-ap-south-1}" \
    --query Parameter.Value \
    --output text
}

ensure_swap() {
  local size_gb="${1:-2}"
  if swapon --show | grep -q '^/swapfile'; then
    echo "Swap already enabled."
    return 0
  fi
  echo "Creating a ${size_gb} GiB swap file at /swapfile."
  echo "The backend loads PyTorch and all-MiniLM-L6-v2. Without swap a 2 GiB instance can still be killed (exit 137) during that load. Swap on EBS is slow; it is the safety net, not the main memory."
  if ! fallocate -l "${size_gb}G" /swapfile; then
    dd if=/dev/zero of=/swapfile bs=1M count="$((size_gb * 1024))" status=progress
  fi
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab
  printf 'vm.swappiness=10\n' >/etc/sysctl.d/99-codelens-swappiness.conf
  sysctl -w vm.swappiness=10 >/dev/null
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    systemctl enable --now docker
    return 0
  fi
  apt-get update
  apt-get install -y ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  # shellcheck disable=SC1091
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    >/etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  if [[ -n "${SUDO_USER:-}" ]] && id "$SUDO_USER" >/dev/null 2>&1; then
    usermod -aG docker "$SUDO_USER"
  fi
}

private_ip() {
  hostname -I | awk '{print $1}'
}

link_app_root() {
  local root="$1"
  mkdir -p /opt/codelens
  if [[ ! -e /opt/codelens/app ]]; then
    ln -s "$root" /opt/codelens/app
  fi
}

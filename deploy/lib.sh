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

# Docker's own apt repository lags new Ubuntu releases. 24.04 uses that
# repository. 26.04 and newer fall back to Ubuntu's docker.io packages, then
# to the get.docker.com installer.
install_docker() {
  export DEBIAN_FRONTEND=noninteractive
  if command -v docker >/dev/null 2>&1; then
    systemctl enable --now docker
    _ensure_docker_compose
    _docker_group
    return 0
  fi

  apt-get update
  apt-get install -y ca-certificates curl

  local codename=""
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    codename="$(. /etc/os-release && printf '%s' "${VERSION_CODENAME:-}")"
  fi

  if [[ -n "$codename" ]] && curl -fsSL -o /dev/null -m 20 \
      "https://download.docker.com/linux/ubuntu/dists/${codename}/Release"; then
    if _install_docker_from_docker_repo "$codename"; then
      _docker_group
      return 0
    fi
    echo "Docker's packages for ${codename} did not install. Falling back to Ubuntu docker.io." >&2
    rm -f /etc/apt/sources.list.d/docker.list
    apt-get update
  else
    echo "Docker's apt repo has no ${codename:-this Ubuntu release}. Installing Ubuntu docker.io." >&2
  fi

  if apt-get install -y docker.io docker-compose-v2; then
    systemctl enable --now docker
    _ensure_docker_compose
    _docker_group
    return 0
  fi

  echo "Ubuntu docker.io is unavailable. Trying https://get.docker.com." >&2
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
  _ensure_docker_compose
  _docker_group
}

_install_docker_from_docker_repo() {
  local codename="$1"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable" \
    >/etc/apt/sources.list.d/docker.list
  apt-get update || return 1
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
    || return 1
  systemctl enable --now docker
}

_ensure_docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    return 0
  fi
  apt-get update
  apt-get install -y docker-compose-v2 || apt-get install -y docker-compose-plugin || true
  if docker compose version >/dev/null 2>&1; then
    return 0
  fi
  local plugin=""
  plugin="$(dpkg -L docker-compose-v2 2>/dev/null | grep -m1 '/docker-compose$' || true)"
  if [[ -n "$plugin" ]]; then
    install -d /usr/local/lib/docker/cli-plugins
    ln -sfn "$plugin" /usr/local/lib/docker/cli-plugins/docker-compose
  fi
}

_docker_group() {
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

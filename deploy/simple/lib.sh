# Helpers for the two-instance deploy. Source this file; do not execute it.

# 24.04 and 26.04 are the tested releases. Anything else, including a newer
# LTS, prints a warning and continues. This function does not exit.
warn_ubuntu_release() {
  local version="${1:-}"
  local pretty="${2:-}"
  if [[ -z "$version" && -z "$pretty" && -r /etc/os-release ]]; then
    local info=""
    # shellcheck disable=SC1091
    info="$(. /etc/os-release && printf '%s\n%s' "${VERSION_ID:-}" "${PRETTY_NAME:-unknown}")"
    version="${info%%$'\n'*}"
    pretty="${info#*$'\n'}"
  fi
  case "$version" in
    24.04|26.04) return 0 ;;
  esac
  echo "Warning: tested on Ubuntu 24.04 and 26.04. This machine is ${pretty:-unknown}. Continuing." >&2
}

# Return 0 when DATA_DIR was left by a failed first start and holds no
# application data. A saved URI means the app user signed in, so the files
# stay. MongoDB 8.0 files cannot be opened by 7.0, and a mongo:8 container
# that never saved a URI never stored application data.
should_clear_failed_mongo_datadir() {
  local data_dir="$1"
  local uri_file="$2"
  local container_image="${3:-}"
  [[ -f "$uri_file" ]] && return 1
  [[ -d "$data_dir" ]] || return 1
  if [[ "$container_image" == mongo:8 || "$container_image" == mongo:8.* ]]; then
    return 0
  fi
  if [[ -f "$data_dir/storage.bson" ]] && grep -a -q '8\.0' "$data_dir/storage.bson"; then
    return 0
  fi
  # mongod exited before creating WiredTiger tables.
  if [[ ! -f "$data_dir/WiredTiger" && ! -f "$data_dir/WiredTiger.wt" ]]; then
    if [[ -f "$data_dir/mongod.lock" || -d "$data_dir/journal" || -d "$data_dir/diagnostic.data" ]]; then
      return 0
    fi
  fi
  return 1
}

trim() {
  local value="$1"
  value="${value//$'\r'/}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

# Read one key from an env file. Values are stored unquoted so Docker Compose
# sees the same text this script reads back. A `?` in a MongoDB URI must not
# go through the shell `source` builtin.
read_env() {
  local key="$1"
  local file="$2"
  local line="" value=""
  [[ -f "$file" ]] || return 0
  line="$(grep -m1 "^${key}=" "$file" || true)"
  value="${line#"${key}"=}"
  if [[ ${#value} -ge 2 && "${value:0:1}" == "'" && "${value: -1}" == "'" ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

# Split a comma-separated Groq key list. Prints one key per line.
# Accepts a single key or up to five. Does not print the keys on failure.
normalize_groq_keys() {
  local raw="$1"
  local part trimmed
  local -a keys=()
  raw="${raw//$'\r'/}"
  IFS=',' read -r -a parts <<< "$raw"
  for part in "${parts[@]}"; do
    trimmed="$(trim "$part")"
    [[ -z "$trimmed" ]] && continue
    keys+=("$trimmed")
  done
  if [[ ${#keys[@]} -eq 0 ]]; then
    echo "At least one Groq API key is required." >&2
    return 1
  fi
  if [[ ${#keys[@]} -gt 5 ]]; then
    echo "Provide at most 5 Groq API keys." >&2
    return 1
  fi
  printf '%s\n' "${keys[@]}"
}

write_env() {
  local key="$1"
  local value="$2"
  local file="$3"
  local tmp
  if [[ "$value" == *$'\n'* || "$value" == *"#"* ]]; then
    echo "$key cannot contain a newline or a hash." >&2
    return 1
  fi
  mkdir -p "$(dirname "$file")"
  tmp="$(mktemp)"
  if [[ -f "$file" ]]; then
    grep -v "^${key}=" "$file" >"$tmp" || true
  fi
  printf '%s=%s\n' "$key" "$value" >>"$tmp"
  mv "$tmp" "$file"
  chmod 600 "$file"
}

# Vercel production and preview hosts. Starlette matches this against the
# whole Origin header, so a lookalike such as evilvercel.app does not pass.
VERCEL_ORIGIN_REGEX='https://([A-Za-z0-9-]+\.)*vercel\.app'

sslip_host() {
  local ip="$1"
  if [[ ! "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Not an IPv4 address: $ip" >&2
    return 1
  fi
  # 13.234.56.78 -> 13-234-56-78.sslip.io, which resolves back to that IP.
  printf '%s.sslip.io' "${ip//./-}"
}

app_mongo_uri() {
  local password="$1"
  local ip="$2"
  local user="${3:-codelens}"
  local db="${4:-codelens}"
  printf 'mongodb://%s:%s@%s:27017/%s?authSource=admin' "$user" "$password" "$ip" "$db"
}

imds_token() {
  curl -fsS -m 2 -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60" || true
}

private_ip() {
  local token="" ip=""
  token="$(imds_token)"
  if [[ -n "$token" ]]; then
    ip="$(curl -fsS -m 2 -H "X-aws-ec2-metadata-token: $token" \
      http://169.254.169.254/latest/meta-data/local-ipv4 || true)"
  fi
  if [[ -z "$ip" ]]; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  fi
  if [[ -z "$ip" ]]; then
    echo "Could not find this instance's private IP." >&2
    return 1
  fi
  printf '%s' "$ip"
}

public_ip() {
  local token="" ip=""
  token="$(imds_token)"
  if [[ -n "$token" ]]; then
    ip="$(curl -fsS -m 2 -H "X-aws-ec2-metadata-token: $token" \
      http://169.254.169.254/latest/meta-data/public-ipv4 || true)"
  fi
  if [[ -z "$ip" ]]; then
    echo "Could not find a public IP. Attach an Elastic IP, then run this again." >&2
    return 1
  fi
  printf '%s' "$ip"
}

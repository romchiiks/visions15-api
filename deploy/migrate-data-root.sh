#!/usr/bin/env sh
set -eu

SOURCE_ROOT="${SOURCE_ROOT:-/opt/visions15}"
DATA_ROOT="${1:-${VISIONS15_DATA_ROOT:-}}"

if [ -z "$DATA_ROOT" ]; then
  echo "Usage: $0 /path/to/new-data-root"
  echo "Example: $0 /mnt/visions15-data"
  exit 2
fi

case "$DATA_ROOT" in
  /|"")
    echo "Refusing to use unsafe DATA_ROOT: $DATA_ROOT"
    exit 2
    ;;
esac

if [ ! -f "$SOURCE_ROOT/docker-compose.yml" ]; then
  echo "docker-compose.yml was not found in SOURCE_ROOT=$SOURCE_ROOT"
  exit 1
fi

for command_name in docker rsync; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command is missing: $command_name"
    exit 1
  fi
done

timestamp="$(date +%Y%m%d-%H%M%S)"

cd "$SOURCE_ROOT"
export VISIONS15_DATA_ROOT="$DATA_ROOT"

echo "Stopping docker compose services in $SOURCE_ROOT"
docker compose down

echo "Creating data root: $DATA_ROOT"
mkdir -p "$DATA_ROOT"

for dir_name in storage files label-studio-data minio-data; do
  mkdir -p "$DATA_ROOT/$dir_name"

  if [ -d "$SOURCE_ROOT/$dir_name" ]; then
    echo "Migrating $SOURCE_ROOT/$dir_name -> $DATA_ROOT/$dir_name"
    rsync -a --delete "$SOURCE_ROOT/$dir_name/" "$DATA_ROOT/$dir_name/"
    mv "$SOURCE_ROOT/$dir_name" "$SOURCE_ROOT/$dir_name.migrated-$timestamp"
  else
    echo "Skipping missing source directory: $SOURCE_ROOT/$dir_name"
  fi
done

if [ -f "$SOURCE_ROOT/.env" ]; then
  cp "$SOURCE_ROOT/.env" "$SOURCE_ROOT/.env.bak-$timestamp"
  if grep -q '^VISIONS15_DATA_ROOT=' "$SOURCE_ROOT/.env"; then
    sed -i "s|^VISIONS15_DATA_ROOT=.*|VISIONS15_DATA_ROOT=$DATA_ROOT|" "$SOURCE_ROOT/.env"
  else
    printf '\nVISIONS15_DATA_ROOT=%s\n' "$DATA_ROOT" >> "$SOURCE_ROOT/.env"
  fi
else
  printf 'VISIONS15_DATA_ROOT=%s\n' "$DATA_ROOT" > "$SOURCE_ROOT/.env"
fi

echo "Starting docker compose services"
docker compose up -d --build

echo "Done. Old directories were kept as *.migrated-$timestamp in $SOURCE_ROOT"

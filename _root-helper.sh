#!/usr/bin/env bash
# The only part that runs as root. Kept deliberately small and auditable.
#   _root-helper.sh install <staged app.asar>
#   _root-helper.sh revert
set -euo pipefail

# The resources directory is passed in - this script assumes no paths, so it
# works wherever Claude Desktop is installed.
case "${1:-}" in
install)
  RES=${2:?resources dir}
  staged=${3:?staged archive}
  TARGET="$RES/app.asar"
  BACKUP="$RES/app.asar.orig"
  [[ -f $staged ]] || { echo "install: staged archive missing" >&2; exit 1; }
  [[ -f $TARGET ]] || { echo "install: $TARGET missing" >&2; exit 1; }

  # Refuse anything that is not an asar carrying our injection.
  # The first 32-bit word of an asar archive is always 4.
  [[ $(head -c 4 "$staged" | od -An -tu4 | tr -d ' ') == 4 ]] \
    || { echo "install: staged file is not an asar archive" >&2; exit 1; }
  grep -qa 'ocean-theme injection' "$staged" \
    || { echo "install: staged archive carries no injection" >&2; exit 1; }

  # Back up the pristine archive. Decide by CONTENT: if the live archive does
  # not carry the injection it IS pristine, so (re)create the backup from it -
  # that refreshes a stale backup left behind by an app update. If it is
  # already patched, keep the existing backup and never overwrite it.
  if grep -qa 'ocean-theme injection' "$TARGET"; then
    [[ -f $BACKUP ]] || { echo "install: target is patched but no backup exists" >&2; exit 1; }
  else
    cp -a "$TARGET" "$BACKUP"
    echo "backed up pristine app.asar ($(stat -c%s "$BACKUP") bytes)"
  fi

  cp "$staged" "$TARGET"
  chmod 644 "$TARGET"
  echo "installed app.asar ($(stat -c%s "$TARGET") bytes)"
  ;;
revert)
  RES=${2:?resources dir}
  TARGET="$RES/app.asar"
  BACKUP="$RES/app.asar.orig"
  if [[ -f $BACKUP ]]; then
    cp -a "$BACKUP" "$TARGET"
    rm -f "$BACKUP"
    chmod 644 "$TARGET"
    echo "restored the original app.asar"
  else
    echo "nothing to revert (no app.asar.orig)"
  fi
  ;;
*)
  echo "usage: _root-helper.sh install <resources-dir> <staged.asar>" >&2
  echo "       _root-helper.sh revert  <resources-dir>" >&2; exit 2 ;;
esac

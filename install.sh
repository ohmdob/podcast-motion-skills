#!/usr/bin/env bash
# Installs the skills for every Claude Code session on this machine, as links back to this folder, so a `git pull` updates them.
#
#   ./install.sh               link the skills, and make a private .env from the example if there is none
#   ./install.sh --uninstall   remove only the links that point here; nothing else is touched
#
# Skills go in $CLAUDE_CONFIG_DIR/skills, or ~/.claude/skills if that isn't set.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
linked=0 skipped=0

if [ "${1:-}" = "--uninstall" ]; then
  for skill in "$REPO"/.claude/skills/*/; do
    link="$DEST/$(basename "$skill")"
    if [ -L "$link" ] && [ "$(readlink "$link")" = "${skill%/}" ]; then
      rm "$link" && echo "removed $link"
    fi
  done
  exit 0
fi

mkdir -p "$DEST"
for skill in "$REPO"/.claude/skills/*/; do
  name="$(basename "$skill")"
  link="$DEST/$name"
  if [ -L "$link" ] && [ "$(readlink "$link")" = "${skill%/}" ]; then
    echo "already linked: $name"
  elif [ -e "$link" ] || [ -L "$link" ]; then
    echo "SKIPPED $name: $link already exists and is not this repo's. Move it away and run this again."
    skipped=$((skipped + 1))
  else
    ln -s "${skill%/}" "$link"
    echo "linked: $name"
    linked=$((linked + 1))
  fi
done

if [ ! -f "$REPO/.env" ]; then
  (umask 077 && cp "$REPO/.env.example" "$REPO/.env")
  echo "made $REPO/.env: put your keys there. It is ignored by git."
fi
chmod 600 "$REPO/.env"
chmod +x "$REPO"/.claude/skills/podcast-playbook/scripts/rvm_matte.py 2>/dev/null || true

echo
echo "$linked linked, $skipped skipped, into $DEST"
echo "Next: python3 \"$REPO/.claude/skills/podcast-playbook/scripts/doctor.py\""
[ "$skipped" -eq 0 ]

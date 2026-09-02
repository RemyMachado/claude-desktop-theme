#!/usr/bin/env bash
# Build the patched app.asar and install it.
#
# The app renders claude.ai remotely, so the theme is injected into the page by
# the Electron main process; that means rebuilding the archive rather than
# editing a stylesheet.
#
# Everything except the final install runs unprivileged, and the archive is
# always rebuilt from the pristine original, so running this twice is the same
# as running it once.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGED="$HERE/app.patched.asar"
source "$HERE/_escalate.sh"

[[ -f "$HERE/claude-theme.css" ]] || {
  echo "no claude-theme.css - run 'python3 generate.py' first" >&2; exit 1; }

# build_asar.py refuses to emit an archive it cannot verify, so a failure here
# means nothing reaches the install step.
rm -f "$STAGED"
python3 "$HERE/build_asar.py" -o "$STAGED"
[[ -f $STAGED ]] || { echo "build produced no archive" >&2; exit 1; }

# Ask the Python side where Claude Desktop is - nothing here assumes a path.
RES=$(python3 -c "import sys; sys.path.insert(0,'$HERE'); import app_tokens; print(app_tokens.resources_dir())") || {
  echo "could not locate the Claude Desktop installation" >&2; exit 1; }
echo "installation: $RES"

escalate "$HERE/_root-helper.sh" install "$RES" "$STAGED"
rm -f "$STAGED"

echo
echo "Now restart the app. On this machine neither the tray's Quit nor the"
echo "window's close button actually kills it, and there is no reload shortcut."
echo "This detaches first, so the restart survives killing its own parent:"
echo
echo "  setsid bash -c 'sleep 1; pkill -f \"$(dirname "$RES")/claude-deskto[p]\"; sleep 3; claude-desktop' >/dev/null 2>&1 &"

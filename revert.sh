#!/usr/bin/env bash
# Restore the app.asar that shipped with the installed build.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/_escalate.sh"
RES=$(python3 -c "import sys; sys.path.insert(0,'$HERE'); import app_tokens; print(app_tokens.resources_dir())") || {
  echo "could not locate the Claude Desktop installation" >&2; exit 1; }
escalate "$HERE/_root-helper.sh" revert "$RES"
echo "Restart Claude Desktop to see the stock theme."

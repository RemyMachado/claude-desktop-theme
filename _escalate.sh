# Sourced helper. Chooses how to become root for the one privileged step.
#
# pkexec is preferred when a desktop session is present: it raises a graphical
# password dialog, so an agent can run apply.sh without needing a password on
# its stdin (which sudo requires and which agents cannot supply).
escalate() {
  if [[ -n ${CLAUDE_THEME_FORCE_SUDO:-} ]]; then
    sudo "$@"
  elif sudo -n true 2>/dev/null; then
    sudo "$@"                                   # credentials already cached
  elif [[ -n ${DISPLAY:-}${WAYLAND_DISPLAY:-} ]] && command -v pkexec >/dev/null; then
    echo "requesting authorisation - approve the password dialog on your desktop..."
    pkexec "$@"
  else
    sudo "$@"                                   # terminal prompt
  fi
}

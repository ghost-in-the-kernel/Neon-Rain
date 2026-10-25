#!/usr/bin/env bash
# The tithe guard (R-012, R-028 (1)): how a commit is made here. A commit whose message starts `tithe:` is always
# accepted; any other is refused while a tithe is due. R-012: every eighth commit is a tithe, so a tithe is due once
# seven commits have landed since the last `tithe:` one (merges not counted; all commits if there is none yet).
# Usage: scripts/commit.sh -F message.txt | -m "message" | -F -   (any git commit arguments)
#        scripts/commit.sh --check   says where the count stands and commits nothing (exit 1 if a tithe is due)
# Works on the repository of the current directory. Never a git hook: nothing installs it, nothing runs it on its own.
# Commits are authored as Ghost (CLAUDE.md) unless git config already says who; this script changes no config.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"

if [ "${1:-}" = "--check" ]; then exec python3 -I "$here/commit_guard.py" --check; fi

# A message on stdin (-F -) is read once into a file, so its subject can be read and git still gets all of it.
args=("$@")
for i in "${!args[@]}"; do
  if [[ "${args[$i]}" == "-F" || "${args[$i]}" == "--file" ]] && [[ "${args[$((i+1))]:-}" == "-" ]]; then
    message_file=$(mktemp); trap 'rm -f "$message_file"' EXIT
    cat > "$message_file"; args[$((i+1))]="$message_file"
  fi
done

python3 -I "$here/commit_guard.py" "${args[@]}" || exit 1

who=()
[ -n "$(git config user.name || true)" ] || who+=(-c user.name=Ghost)
[ -n "$(git config user.email || true)" ] || who+=(-c user.email=118085043+ghost-in-the-kernel@users.noreply.github.com)
git "${who[@]}" commit "${args[@]}"

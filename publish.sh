#!/usr/bin/env bash
# Repo'ni GitHub'ga bitta buyruqda joylaydi.
# Ishlatish:
#   bash publish.sh                       # gh CLI bo'lsa: repo'ni ham yaratadi
#   bash publish.sh <remote-url>          # tayyor remote URL bilan
set -euo pipefail
cd "$(dirname "$0")"

REPO_NAME="prompt-injection-lab"
REMOTE="${1:-}"

git init -q
git add .
git commit -qm "Prompt injection lab (PoC) — educational" || true
git branch -M main

if [ -n "$REMOTE" ]; then
  git remote remove origin 2>/dev/null || true
  git remote add origin "$REMOTE"
  git push -u origin main
elif command -v gh >/dev/null 2>&1; then
  gh repo create "$REPO_NAME" --public --source=. --push
else
  echo "!! gh CLI yo'q va remote URL berilmadi."
  echo "   Avval GitHub'da bo'sh repo oching, keyin:"
  echo "   bash publish.sh https://github.com/umid1988/$REPO_NAME.git"
  exit 1
fi

echo "✅ Tayyor. Tekshiring: git remote -v"

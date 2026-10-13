#!/bin/zsh
# Checks Top4Running from this Mac (it blocks GitHub's servers) and saves to GitHub.
# Run by launchd: ~/Library/LaunchAgents/com.alphabuys.check.plist
cd "$(dirname "$0")" || exit 1
git pull --rebase -q || exit 1
/usr/bin/python3 check.py Top4Running
git add data
git diff --cached --quiet && exit 0
git commit -qm "Prices (Mac) $(date -u +'%Y-%m-%d %H:%M')"
git push -q || { git pull --rebase -q && git push -q; }

#!/bin/sh
cd "$(dirname "$0")" || exit 1
printf '\n  btvs-recomp — launcher update\n\nClose the game and launcher, then choose your existing project folder.\nOnly the launcher is built. Saves, game files and HD packs are kept.\n\n'
/usr/bin/python3 tools/update_launcher.py --source "$PWD" --choose-target --human
result=$?
printf '\nPress Return to close this window.\n'
read -r answer
exit "$result"

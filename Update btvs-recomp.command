#!/bin/sh
cd "$(dirname "$0")" || exit 1
printf '\n  btvs-recomp — update\n\nClose the game and launcher, then choose your existing project folder.\nThe game is rebuilt automatically if required. Saves, imported game files and HD packs are kept.\n\n'
/usr/bin/python3 tools/update_launcher.py --source "$PWD" --choose-target --human
result=$?
printf '\nPress Return to close this window.\n'
read -r answer
exit "$result"

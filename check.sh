#!/usr/bin/env bash

# run this with a cron job

USER=""
FLAIRBOT_DIR=""

su -c "cd $FLAIRBOT_DIR; ./flairbot.py" $USER

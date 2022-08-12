#!/bin/bash
# Shell script to load necessary dependencies before running app.
clear
echo "[PIPE] Loading Pipeline Base..."
# ================================================================

AU_COMPANY_NAME=after
export AU_COMPANY_NAME

# Pipeline path:
if [ -z "$AU_PIPE_BASE" ]
then
  AU_PIPE_BASE="/tech/library/pipeline/$AU_COMPANY_NAME"
  export AU_PIPE_BASE
fi

# echo "[AU_PIPE_BASE]: $AU_PIPE_BASE"
# DEVS:
AU_PIPE_DEV_PATH="$AU_PIPE_BASE/dev"
export AU_PIPE_DEV_PATH

# CONFIGS:
AU_PIPE_CONFIG_PATH="$AU_PIPE_BASE/config"
export AU_PIPE_CONFIG_PATH


# ================================================================

echo "[PIPE] Loading Api..."

# API BASE:
AU_PIPE_API_PATH="$AU_PIPE_DEV_PATH/api"
export AU_PIPE_API_PATH

# 1.  AUTOM8 API:
export AU_PIPE_AUTOM8_API="$AU_PIPE_API_PATH/autom8_api"  # import core, sn_shotgun, utils
export PYTHONPATH+=:$AU_PIPE_AUTOM8_API
# echo "[AUTOM8 API PATH]: $AU_PIPE_AUTOM8_API"

# 2. Shotgun API:
export AU_PIPE_SHOTGUN_API="$AU_PIPE_API_PATH/shotgun"  # import shotgun_api3
export PYTHONPATH+=:$AU_PIPE_SHOTGUN_API

# Load Python2.7 Libraries
source "$AU_PIPE_API_PATH/site_packages/Python_libs_2.7.5.sh"

# Load Python3.7 Libraries
# source "$AU_PIPE_API_PATH/site_packages/Python_libs_3.7.11.sh"

# ================================================================

# shellcheck disable=SC2128
# shellcheck disable=SC2006
script_path=`realpath "$BASH_SOURCE"`
# shellcheck disable=SC2006
current_directory=`dirname "$script_path"`
# shellcheck disable=SC2164
# shellcheck disable=SC2086
cd  $current_directory
#echo "[PATH]: $current_directory"
# shellcheck disable=SC2086
python ShotMaker $1
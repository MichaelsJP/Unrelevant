#!/bin/bash
#
# This script automates the setup of the underlying project.
# Copyright (c) 2021 Julian Psotta - julianpsotta@gmail.com

################################################################################
#                          Automated Setup Helper                              #
#                                                                              #
#                          Insert Description here                             #
#                                                                              #
#                                                                              #
################################################################################
################################################################################
################################################################################
#                                                                              #
#  Copyright (C) 2020, Julian Psotta                                           #
#  julianpsotta@gmail.com                                                      #
#                                                                              #
#                                                                              #
################################################################################
################################################################################
################################################################################

################################################################################
# Help                                                                         #
################################################################################

usage() {
  set +x
  cat 1>&2 <<HERE

Script for setting up the project.
USAGE:
    ./setup.sh [OPTIONS]

OPTIONS (setup the project):
  -r <REFRESH_DOCKER>        Refresh the docker setup if it exists.
  -o <OUT_DIRECTORY>         Provide an output directory.
  -w <OVERWRITE_OUTPUT>      Provide to overwrite the output directory it exists.
  -h                         Print help
  -v                         Print the script version

EXAMPLES:
# Remote configs with ors tag checkout
./setup.sh -o output

HERE
}

START_DIRECTORY="$(
  cd "$(dirname "$0")" >/dev/null 2>&1
  pwd -P
)"

################################################################################
# Import helper functions                                                      #
################################################################################
SCRIPT_NAME="docker-setup"
if [[ ! -d "$DIR" ]]; then DIR="$PWD"; fi
. "$START_DIRECTORY/libs/helper_functions.sh"

################################################################################
# Initialize main variables                                                    #
################################################################################
SCRIPT_VERSION="0.0.1"
################################################################################
# Initialize main functions                                                    #
################################################################################

download_population_dataset() {
  local dataset_url="https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/0_Mosaicked/ppp_2020_1km_Aggregated.tif"
  local current_directory=$PWD
  local dataset_local_path="${current_directory}/population.tif"
  if [ -e "${dataset_local_path}" ]; then
    say "Population dataset exists. Skipping download"
    echo "${dataset_local_path}"
  else
    say "Download the population dataset. This will take some time."
    curl --header "Host: data.worldpop.org" --user-agent "Mozilla/5.0 (X11; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0" --header "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" --header "Accept-Language: en-US,en;q=0.5" --header "Upgrade-Insecure-Requests: 1" --header "Sec-Fetch-Dest: document" --header "Sec-Fetch-Mode: navigate" --header "Sec-Fetch-Site: none" --header "Sec-Fetch-User: ?1" "$dataset_url" --output "${dataset_local_path}"
    say "Successfully downloaded $dataset_local_path"
    echo "${dataset_local_path}"
  fi
}

################################################################################
################################################################################
# Main program                                                                 #
################################################################################
################################################################################
main() {
  export DEBIAN_FRONTEND=noninteractive

  CheckLinuxSystem
  CheckNonRoot
  check_program_installed docker
  check_program_installed docker-compose

  while builtin getopts "hvrwo:" opt "${@}"; do
    case $opt in
    h)
      usage
      exit 0
      ;;
    v)
      say "Script Version: $SCRIPT_VERSION"
      exit 0
      ;;
    r)
      REFRESH_DOCKER=true
      ;;
    o)
      OUT_DIRECTORY=$OPTARG
      if ! [[ -d "$OUT_DIRECTORY" ]]; then
        err "You must provide an existing output folder."
      fi
      CheckWriteAccess "$OUT_DIRECTORY"
      OUT_DIRECTORY=$(realpath "$OUT_DIRECTORY")
      ;;
    w)
      OVERWRITE_OUTPUT=true
      ;;
    \?)
      err "Invalid option: -$OPTARG" >&2
      ;;

    :)
      err "Option -$OPTARG requires an argument."
      ;;
    *)
      err "Option -$OPTARG not known."
      ;;
    esac
  done

  # Initialize helper variables
  # Check mandatory
  check_mandatory_argument "OUT_DIRECTORY" "$OUT_DIRECTORY"
  check_mandatory_argument "OVERWRITE_OUTPUT" "$OVERWRITE_OUTPUT" false
  check_mandatory_argument "REFRESH_DOCKER" "$REFRESH_DOCKER" false

  # Create output folder
  OUT_DIRECTORY=$(create_folder "$OUT_DIRECTORY" "$OVERWRITE_OUTPUT")

  # Refresh the docker setup
  if [ "$REFRESH_DOCKER" == "true" ] || [ "$REFRESH_DOCKER" == "True" ] || [ "$REFRESH_DOCKER" == "TRUE" ]; then
    say "Refreshing docker setup"
    docker_container_clean unrelevant 2
  fi
  docker-compose -f "$START_DIRECTORY/.docker/docker-compose.yml" up -d
  docker exec -it unrelevant /bin/bash -c "export PGPASSWORD=admin && psql -h postgres -U admin gis -c 'CREATE EXTENSION IF NOT EXISTS postgis_raster';"
  # Download the population dataset if not present
  POPULATION_DATASET=$(download_population_dataset)



  # Setting defaults
  #  check_mandatory_argument "CONFIG_PREFIX" "$CONFIG_PREFIX" "app.config."
  #  check_mandatory_argument "CONFIG_POSTFIX" "$CONFIG_POSTFIX" ".json"
  #  check_mandatory_argument "OVERWRITE_OUTPUT" "$OVERWRITE_OUTPUT" "false"

  cleanup
}
# Must be the last statement
main "$@" || exit 1
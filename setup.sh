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
DOCKER_DATABASE_CONTAINER_NAME="unrelevant"
DOCKER_ORS_CONTAINER_NAME="ors-app"
POPULATION_TABLE="wpop"
################################################################################
# Initialize main functions                                                    #
################################################################################

download_population_dataset() {
  local current_directory=$PWD
  # shellcheck disable=SC2164
  cd "$START_DIRECTORY"
  local dataset_url="https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/0_Mosaicked/ppp_2020_1km_Aggregated.tif"
  local dataset_local_path="${START_DIRECTORY}/data/population.tif"
  if [ -e "${dataset_local_path}" ]; then
    say "Population dataset exists. Skipping download."
    echo "${dataset_local_path}"
  else
    say "Download the population dataset. This will take some time."
    curl --header "Host: data.worldpop.org" --user-agent "Mozilla/5.0 (X11; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0" --header "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" --header "Accept-Language: en-US,en;q=0.5" --header "Upgrade-Insecure-Requests: 1" --header "Sec-Fetch-Dest: document" --header "Sec-Fetch-Mode: navigate" --header "Sec-Fetch-Site: none" --header "Sec-Fetch-User: ?1" "$dataset_url" --output "${dataset_local_path}"
    say "Successfully downloaded ${dataset_local_path}."
    echo "${dataset_local_path}"
  fi
  # shellcheck disable=SC2164
  cd "$current_directory"
}

download_germany_osm_pbf_dataset() {
  local current_directory=$PWD
  # shellcheck disable=SC2164
  cd "$START_DIRECTORY"
  local dataset_url="http://download.geofabrik.de/europe/germany-latest.osm.pbf"
  local dataset_local_path="${START_DIRECTORY}/data/germany.osm.pbf"
  if [ -e "${dataset_local_path}" ]; then
    say "OSM dataset exists. Skipping download."
    echo "${dataset_local_path}"
  else
    say "Download the osm dataset. This will take some time."
    curl --header "Host: download.geofabrik.de" --header "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36" --header "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9" --header "Accept-Language: en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7,en-GB;q=0.6" "$dataset_url" -L -o "${dataset_local_path}"
    say "Successfully downloaded ${dataset_local_path}."
    echo "${dataset_local_path}"
  fi
  # shellcheck disable=SC2164
  cd "$current_directory"
}

download_ohsome_dataset() {
  local dataset_url="https://downloads.ohsome.org/OSHDB/v0.6/europe/germany/baden-wuerttemberg/heidelberg_68900_2020-07-23.oshdb.mv.db"
  local current_directory=$PWD
  local dataset_local_path="${current_directory}/ohsome.oshdb.mv.db"
  if [ -e "${dataset_local_path}" ]; then
    say "Ohsome database exists. Skipping download."
    echo "${dataset_local_path}"
  else
    say "Download the ohsome database. This will take some time."
    curl --header "Host: downloads.ohsome.org" --user-agent "Mozilla/5.0 (X11; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0" --header "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" --header "Accept-Language: en-US,en;q=0.5" --header "Upgrade-Insecure-Requests: 1" --header "Sec-Fetch-Dest: document" --header "Sec-Fetch-Mode: navigate" --header "Sec-Fetch-Site: none" --header "Sec-Fetch-User: ?1" "$dataset_url" --output "${dataset_local_path}"
    say "Successfully downloaded ${dataset_local_path}."
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
  check_program_installed tar
  check_program_installed python

  while builtin getopts "hvrwo:" opt "${@}"; do
    case $opt in
    h)
      usage
      exit 0
      ;;
    v)
      say "Script Version: $SCRIPT_VERSION."
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

  # Get the population data set
  POPULATION_DATASET_PATH=$(download_population_dataset)

  # Get the germany pbf data set
  OSM_GERMANY_DATASET_PATH=$(download_germany_osm_pbf_dataset)

  # Unpack the shipped nuts boundaries
  say "Unpack the nuts boundary layers:"
  NUTS_DATASET_PATH="$START_DIRECTORY/data/nuts.tar.xz"
  tar -xvf "$NUTS_DATASET_PATH" -C "$START_DIRECTORY/data"

  # Refresh the docker setup
  if [ "$REFRESH_DOCKER" == "true" ] || [ "$REFRESH_DOCKER" == "True" ] || [ "$REFRESH_DOCKER" == "TRUE" ]; then
    say "Refreshing docker setup."
    docker_container_clean "$DOCKER_DATABASE_CONTAINER_NAME" 2
  fi
  say "Starting the docker-compose stack."
  docker-compose -f "$START_DIRECTORY/docker-compose.yml" up --force-recreate -d > /dev/null 2>&1
  sleep 2
  # Wait for the database to be ready
  CONTAINER_STATUS=""
  say "Waiting for the database to become ready."
  while [[ "${CONTAINER_STATUS}" != *"- accepting connections"* ]]; do
    CONTAINER_STATUS=$(docker exec -it "$DOCKER_DATABASE_CONTAINER_NAME" /bin/bash -c "export PGPASSWORD=admin && pg_isready -U admin -h postgres;")
    sleep 1
  done

#  docker exec -it "$DOCKER_DATABASE_CONTAINER_NAME" /bin/bash -c "export PGPASSWORD=admin && psql -h postgres -U admin gis -c 'CREATE EXTENSION IF NOT EXISTS postgis_raster';"

  # Copy the population dataset to the container
  docker cp "$POPULATION_DATASET_PATH" "$DOCKER_DATABASE_CONTAINER_NAME":/scripts/population.tif

  # Run the import inside the
  say "Installing postgis inside the docker image."
  docker exec -it "$DOCKER_DATABASE_CONTAINER_NAME" /bin/bash -c "apt-get update && apt-get install -y postgis" > /dev/null 2>&1
  POPULATION_TABLE_EXISTS=$(docker exec -it "$DOCKER_DATABASE_CONTAINER_NAME" /bin/bash -c "export PGPASSWORD=admin && psql -h postgres -U admin -d gis -c '\dt ${POPULATION_TABLE}'")
  if [[ $POPULATION_TABLE_EXISTS == *"Did not find any relation named"* ]]
  then
    say "Importing the population dataset. This will take some time."
    docker exec -it "$DOCKER_DATABASE_CONTAINER_NAME" /bin/bash -c "export PGPASSWORD=admin && raster2pgsql -Y -c -C -I -M -t 250x250 /scripts/population.tif ${POPULATION_TABLE} | psql -h postgres -U admin gis" > /dev/null 2>&1
  else
    say "Population table exists. Skipping import."
  fi

  say "Waiting for ors to become ready."
  API_STATUS=""
  while [[ "${API_STATUS}" != *"{\"status\":\"ready\"}"* ]]; do
    API_STATUS=$(docker exec -it "$DOCKER_ORS_CONTAINER_NAME" /bin/bash -c "curl http://localhost:8080/ors/health")
    sleep 1
  done

  # Setting defaults
  #  check_mandatory_argument "CONFIG_PREFIX" "$CONFIG_PREFIX" "app.config."
  #  check_mandatory_argument "CONFIG_POSTFIX" "$CONFIG_POSTFIX" ".json"
  #  check_mandatory_argument "OVERWRITE_OUTPUT" "$OVERWRITE_OUTPUT" "false"
  cleanup
}
# Must be the last statement
main "$@" || exit 1

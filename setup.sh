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
  -p <POPUPLATION_DATASET    Provide the path to your population data set in tif format.
  -h                         Print help
  -v                         Print the script version

EXAMPLES:
# Remote configs with ors tag checkout
./setup.sh -o output -p ./population.tif

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
DOCKER_DATABASE_CONTAINER_NAME="unrelevant-postgres"
DOCKER_ORS_CONTAINER_NAME="unrelevant-ors-app"
POPULATION_TABLE="wpop"
################################################################################
# Initialize main functions                                                    #
################################################################################

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
  check_program_installed unzip

  while builtin getopts "hvrwo:p:" opt "${@}"; do
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
    p)
      POPULATION_DATASET_PATH=$OPTARG
      if ! [[ -f "$POPULATION_DATASET_PATH" ]]; then
        err "You must provide an existing  population data set."
      fi
      POPULATION_DATASET_PATH=$(realpath "$POPULATION_DATASET_PATH")
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
  check_mandatory_argument "POPULATION_DATASET" "$POPULATION_DATASET_PATH"
  check_mandatory_argument "OUT_DIRECTORY" "$OUT_DIRECTORY"
  check_mandatory_argument "OVERWRITE_OUTPUT" "$OVERWRITE_OUTPUT" false
  check_mandatory_argument "REFRESH_DOCKER" "$REFRESH_DOCKER" false

  # Create output folder
  OUT_DIRECTORY=$(create_folder "$OUT_DIRECTORY" "$OVERWRITE_OUTPUT")

  # Refresh the docker setup
  if [ "$REFRESH_DOCKER" == "true" ] || [ "$REFRESH_DOCKER" == "True" ] || [ "$REFRESH_DOCKER" == "TRUE" ]; then
    say "Refreshing docker setup."
    docker-compose -f "$START_DIRECTORY/docker-compose.yml" down -v --rmi=local > /dev/null 2>&1
  fi
  say "Stopping docker-compose stack."
  docker-compose -f "$START_DIRECTORY/docker-compose.yml" down > /dev/null 2>&1
  sleep 2
  say "Starting the docker-compose stack."
  docker-compose -f "$START_DIRECTORY/docker-compose.yml" up -d
  sleep 2
  # Wait for the database to be ready
  CONTAINER_STATUS=""
  say "Waiting for the database to become ready."
  while [[ "${CONTAINER_STATUS}" != *"- accepting connections"* ]]; do
    CONTAINER_STATUS=$(docker exec -it "$DOCKER_DATABASE_CONTAINER_NAME" /bin/bash -c "export PGPASSWORD=admin && pg_isready -U admin -h postgres;")
    sleep 1
  done

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

  cleanup
}
# Must be the last statement
main "$@" || exit 1

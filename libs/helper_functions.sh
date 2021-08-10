#!/bin/bash
#
#
#
# Copyright (c) 2020 Julian Psotta - julianpsotta@gmail.com

################################################################################
#                             Helper Functions                                 #
#                                                                              #
# This is a bash helper collection designed to write and design coherent       #
# bash scripts.                                                                #
#                                                                              #
#                                                                              #
################################################################################
################################################################################
################################################################################
#                                                                              #
#  Copyright (C) 2021, Julian Psotta                                           #
#  julianpsotta@gmail.com                                                      #
#                                                                              #
#                                                                              #
################################################################################
################################################################################
################################################################################

##################
### How to use ###
##################
# Put this library in the same folder as you main script and call the library
# before you make use of any imported vars and functions.

#START_DIRECTORY="$(
#  cd "$(dirname "$0")" >/dev/null 2>&1
#  pwd -P
#)"
#
#SCRIPT_NAME="awsome-script"
#if [[ ! -d "$DIR" ]]; then DIR="$PWD"; fi
#. "$START_DIRECTORY/helper_functions.sh"

#say "Awsome script started"

###################################################################################
# Global vars and functions. Override if needed                                   #
###################################################################################

get_time() {
  # Return a well formatted time string in the format xx Days xx Hours xx Minutes xx Seconds from a start time.
  echo "$(date +'%d/%m/%Y_%H:%M:%S')"
}

# Set this variable in the main Script to give error and other print statements a proper script name.
SCRIPT_NAME=${SCRIPT_NAME:-"HELPER-SCRIPT"}
HOST_NAME=$(uname -n) # Get the instance name
ROCKET_URL=${ROCKET_URL:-""}

OK_COLOR=${OK_COLOR:-"\e[42m"}
WARN_COLOR=${WARN_COLOR:-"\e[43m"}
ERROR_COLOR=${ERROR_COLOR:-"\e[101m"}
UNDERLINE_TEXT=${UNDERLINE_TEXT:-"\e[4m"}
NEWLINE=${NEWLINE:-"\n"}
END_CUSTOM_SYNTAX=${END_CUSTOM_SYNTAX:-"\e[0m"}

say_to_rocket() {
  # Tell rocket something
  # $1 message body
  # $2 level_color. OK,WARNING,ERROR. Default is OK
  local msgBody
  local level
  local level_color
  msgBody=$1
  if [ "$2" == "WARNING" ]; then
    level="WARNING"
    level_color="#ff9500"
  elif [ "$2" == "ERROR" ]; then
    level="ERROR"
    level_color="#a11313"
  else
    level="OK"
    level_color="#29bf26"
  fi
  if [[ "${ROCKET_URL}" && "${msgBody}" ]]; then
    local payLoad
    payLoad=$(jo -p text="\\\[\underline{HOSTNAME:${HOST_NAME}}\Downarrow\]${msgBody}" attachments="$(jo -a "$(jo title="${SCRIPT_NAME}" text="Loglevel ${level}" color="${level_color}")")")
    # shellcheck disable=SC1083
    statusCode=$(curl \
      --write-out %{http_code} \
      --silent \
      --output /dev/null \
      -XPOST \
      -H 'Content-type: application/json' \
      -d "${payLoad}" "${ROCKET_URL}")
    if [ "$statusCode" != "200" ]; then
      warn "Rocket chat message couldn't be send with error ${statusCode} and payload: ${payLoad}."
    fi
  else
    warn "Rocket chat messages are not configured correctly. Skipping rocket chat message."
  fi
}

say() {
  # Say something nicely coloured with the prepending script name.
  # $1 What do you have to say ? :)
  # $2 "true" to Override last output and keep writing on the last line. Default is "false"
  # $3 "true" to force a new line. Is ignored if $2 is true.
  if [ "$2" == "true" ]; then
    echo -en "\r${OK_COLOR}($(get_time) | OK | ${HOST_NAME}):${END_CUSTOM_SYNTAX} $1"
  elif [ "$3" == "true" ]; then
    echo -e "${NEWLINE}${OK_COLOR}($(get_time) | OK | ${HOST_NAME}):${END_CUSTOM_SYNTAX} $1" >&2
  else
    echo -e "${OK_COLOR}($(get_time) | OK | ${HOST_NAME}):${END_CUSTOM_SYNTAX} $1" >&2
  fi
}

################################################################################
# Initialize CLEANUP functions                                                 #
################################################################################

# Add all files and folders with absolut path in this list to clean after script run or exit.
# The script is always picked up when not cleaned after the lat run in its current state.
# Temp files will be deleted once the cleanup routine is hit.
CLEANUP_FILE="/tmp/.cleanup_$SCRIPT_NAME"
say "Using $CLEANUP_FILE for the clean-up routine."

add_to_cleanup() {
  # Add items to the cleanup list
  # $1 absolut path of the item to add
  if [[ -n $1 ]]; then
    say "Add $1 to CLEANUP"
    # Two cleanups. One on script exit and one on user exit aka. ctrl+c.
    echo "$1" >>"$CLEANUP_FILE"
  fi
}

cleanup() {
  echo "============================"
  say "Initializing Cleanup-Routine incase trap didn't catch it."
  while IFS= read -r line; do
    say "Cleaning $line"
    rm -rf "$line"
  done <"$CLEANUP_FILE"
  rm -rf "$CLEANUP_FILE"
  echo "============================"
}

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT

function ctrl_c() {
  say "Trapped CTRL-C"
  err "Script was manually canceled"
}

################################################################################
# Initialize LOGGING functions                                                 #
################################################################################

warn() {
  # Warn something coloured with the prepending script name.
  # $1 What do you have to say ? :)
  # $2 "true" to Override last output and keep writing on the last line. Default is "false"
  # $3 "true" to force a new line. Is ignored if $2 is true.
  if [ "$2" == "true" ]; then
    echo -en "\r${WARN_COLOR}($(get_time) | WARN | ${HOST_NAME}):${END_CUSTOM_SYNTAX} $1"
  elif [ "$3" == "true" ]; then
    echo -e "${NEWLINE}${WARN_COLOR}($(get_time) | WARN | ${HOST_NAME}):${END_CUSTOM_SYNTAX} $1" >&2
  else
    echo -e "${WARN_COLOR}($(get_time) | WARN | ${HOST_NAME}):${END_CUSTOM_SYNTAX} $1" >&2
  fi
}

err() {
  # Custom error function to control error throws.
  # $1 is the error reason and must be a string.
  # $2 is the error code, for the correct code see: https://tldp.org/LDP/abs/html/exitcodes.html
  # If no error code is set or the int is smaller 1 or greater 255, 1 is thrown.

  # Exit Code Number	  Meaning	                                                    Example	                Comments
  # 1   	              Catchall for general errors	                                let "var1 = 1/0"	        Miscellaneous errors, such as "divide by zero" and other impermissible operations
  # 2   	              Misuse of shell builtins (according to Bash documentation)  empty_function() {}	      Missing keyword or command, or permission problem (and diff return code on a failed binary file comparison).
  # 126   	            Command invoked cannot execute	                            /dev/null	                Permission problem or command is not an executable
  # 127   	            "command not found"	                                        illegal_command	          Possible problem with $PATH or a typo
  # 128   	            Invalid argument to exit	                                  exit 3.14159	            exit takes only integer args in the range 0 - 255 (see first footnote)
  # 128+n	              Fatal error signal "n"	                                    kill -9 $PPID of script	  $? returns 137 (128 + 9)
  # 130   	            Script terminated by Control-C	                            Ctl-C	                    Control-C is fatal error signal 2, (130 = 128 + 2, see above)
  # 255*	              Exit status out of range	                                  exit -1	                  exit takes only integer args in the range 0 - 255
  ERROR_REASON=$1
  ERROR_CODE=$2
  if [ -z "$ERROR_REASON" ]; then
    ERROR_REASON=Undefined error code
  fi
  if [ -z "$ERROR_CODE" ]; then
    ERROR_CODE=1
  elif [ $ERROR_CODE -lt 1 ]; then
    ERROR_CODE=1
  elif [ $ERROR_CODE -gt 255 ]; then
    ERROR_CODE=1
  fi
  echo -e "${NEWLINE}${ERROR_COLOR}($(get_time) | ERROR | ${HOST_NAME})${END_CUSTOM_SYNTAX} ${ERROR_REASON}" >&2
  say_to_rocket "${ERROR_REASON}" "ERROR"
  cleanup
  exit $ERROR_CODE
}

dependency_found() {
  echo -e "${OK_COLOR}($(get_time) | OK | ${HOST_NAME}):${END_CUSTOM_SYNTAX} ${UNDERLINE_TEXT}Dependency check${END_CUSTOM_SYNTAX} ${1}"
}

dependency_not_found() {
  echo -e "${ERROR_COLOR}($(get_time) | ERROR | ${HOST_NAME}):${END_CUSTOM_SYNTAX} ${UNDERLINE_TEXT}Dependency check${END_CUSTOM_SYNTAX} ${1}"
  cleanup
  exit 1
}

################################################################################
# Initialize helper functions                                                  #
################################################################################
piper() {
  # Useful to have a turning pipe. This function returns the next "pipe" position based on a given.
  # $1 Start pipe position. Defaults to "|"
  if [ "$1" == "|" ] || [ -z "$1" ]; then
    echo "/"
  elif [ "$1" == "/" ]; then
    echo "_"
  elif [ "$1" == "_" ]; then
    echo "\\"
  elif [ "$1" == "\\" ]; then
    echo "|"
  fi

}

vercomphelper() {
  #  Compares version numbers.
  #  $1 first version
  #  $2 second version
  #  Returns the following results
  #  0) op='=';;
  #  1) op='>';;
  #  2) op='<';;
  if [[ $1 == "$2" ]]; then
    return 0
  fi
  local IFS=.
  local i ver1=($1) ver2=($2)
  # fill empty fields in ver1 with zeros
  for ((i = ${#ver1[@]}; i < ${#ver2[@]}; i++)); do
    ver1[i]=0
  done
  for ((i = 0; i < ${#ver1[@]}; i++)); do
    if [[ -z ${ver2[i]} ]]; then
      # fill empty fields in ver2 with zeros
      ver2[i]=0
    fi
    if ((10#${ver1[i]} > 10#${ver2[i]})); then
      return 1
    fi
    if ((10#${ver1[i]} < 10#${ver2[i]})); then
      return 2
    fi
  done
  return 0
}

version_comparison() {
  #  Compares version numbers.
  #  $1 first version
  #  $2 second version
  vercomphelper $1 $2
  case $? in
  0) echo '=' ;;
  1) echo '>' ;;
  2) echo '<' ;;
  esac
}

realpath() {
  # $1 : relative filename
  # $2 : break on error true/false. Default true if not set.
  local folder_name=${1}
  local break_on_error=${2:-true}
  if [[ -n "$folder_name" ]] && [[ -d "$(dirname "$folder_name")" ]]; then
    echo "$(cd "$(dirname "$folder_name")" && pwd)/$(basename "$folder_name")"
  elif [ "$break_on_error" != false ]; then
    err "Can't return absolute path for $folder_name"
  else
    echo ""
  fi
}

check_ssh_access() {
  # Check if the Key-agent has access to the given ssh url
  # $1 ssh URL to check ssh access for.
  if ! ssh -q "$1" exit; then
    err "SSH/Key-agent not configured to access $1. Either provide an URL with git credentials or configure your Key-agent properly."
  fi
}

check_git_access() {
  # Check if the url is accessible either with git credentials provided in the url or with a proper local Key-agent and ssh access.
  # $1 git url to check
  if ! git ls-remote "$1" >/dev/null; then
    err "Couldn't access git at $1. Check the URL! If non-public either provide in url git credentials or configure your local Key-agent accordingly to have ssh access."
  fi
}

clean_prefix_postfix() {
  # Clean a pre- and postfix from a string.
  # $1 the string to be cleaned
  # $2 prefix to be stripped
  # $3 postfix to be stripped
  config=$(echo "$1" | sed -e "s/^$2//" -e "s/$3$//")
  echo "$config"
}

create_random_temp_folder() {
  TEMPORARY_FOLDER="$(mktemp -d)"
  add_to_cleanup "$TEMPORARY_FOLDER"
  say "${UNDERLINE_TEXT}Created temporary folder${END_CUSTOM_SYNTAX}: $TEMPORARY_FOLDER"
  echo "$TEMPORARY_FOLDER"
}

create_folder() {
  # Creates a folder and returns the absolute path
  # $1 Folder path
  # $2 overwrite true/false
  local START_DIRECTORY=$PWD
  if [ -e "$1" ]; then
    if [ "$2" == "true" ] || [ "$2" == "True" ] || [ "$2" == "TRUE" ]; then
      say "Overwriting folder $1"
      rm -rf "$1"
      mkdir -p "$1"
    else
      warn "Folder $1 exists. Be careful."
    fi
  else
    say "Creating folder $1"
    mkdir -p "$1"
  fi
  cd "$1" || err "Couldn't change folder to $1"
  echo "$PWD"
  cd "$START_DIRECTORY"
}

get_free_port() {
  # Check for open ports in a given range
  # If no range is given, it is chosen automatically
  local LOWER_PORT=${1}
  local UPPER_PORT=${2}
  if [ -z "${LOWER_PORT}" ]; then
    say "No lower port given. Selecting it automatically."
    read -r LOWER_PORT _ </proc/sys/net/ipv4/ip_local_port_range
  fi
  if [ -z "${UPPER_PORT}" ]; then
    say "No upper port given. Selecting it automatically."
    read -r _ UPPER_PORT </proc/sys/net/ipv4/ip_local_port_range
  fi
  say "Selecting open port in range $LOWER_PORT - $UPPER_PORT"
  local IS_FREE
  IS_FREE="$(netstat -tapln | grep "$LOWER_PORT")"

  while [[ -n "$IS_FREE" ]] && [[ $LOWER_PORT -le $UPPER_PORT ]]; do
    local LOWER_PORT=$((LOWER_PORT + 1))
    IS_FREE=$(netstat -tapln | grep "$LOWER_PORT")
  done
  if [[ "$LOWER_PORT" -gt "$UPPER_PORT" ]]; then
    say "No open port found in range: $LOWER_PORT - $UPPER_PORT"
    exit 1
  fi
  say "Found open port: $LOWER_PORT"
  echo "$LOWER_PORT"
}

docker_container_clean() {
  # Start a container by image name and remove old running containers.
  # $1 container name.
  # $2 Time to sleep after cleanup. Defaults to 5 seconds
  local CONTAINER_NAME=${1}
  local SLEEP_TIME=${2}
  say "Cleaning leftovers for container: ${CONTAINER_NAME}"
  if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
    if [ "$(docker ps -aq -f status=exited -f name="${CONTAINER_NAME}")" ]; then
      # Remove exited container
      docker rm -f -v "${CONTAINER_NAME}" >/dev/null || err "Couldn't delete container: ${CONTAINER_NAME}"
    else
      # Stop and remove running container
      docker stop "${CONTAINER_NAME}" >/dev/null || err "Couldn't stop container: ${CONTAINER_NAME}"
      docker rm -f -v "${CONTAINER_NAME}" >/dev/null || err "Couldn't delete container: ${CONTAINER_NAME}"
    fi
  fi
  if [ -z "${SLEEP_TIME}" ]; then
    local SLEEP_TIME=5
  fi
  if [ $SLEEP_TIME -gt 0 ]; then
    say "Sleep ${SLEEP_TIME} seconds to let docker finish whatever its doing."
    sleep ${SLEEP_TIME}
  fi
}

timer() {
  # Return a well formatted time string in the format xx Days xx Hours xx Minutes xx Seconds from a start time.
  # Use a start time like this: "local start=$(date +%s)"
  # $1 Start time
  local start=${1}
  local end
  local dt
  local dd
  local dt2
  local dh
  local dt3
  local dm
  local ds
  end=$(date +%s)
  dt=$(echo "$end - $start" | bc)
  dd=$(echo "$dt/86400" | bc)
  dt2=$(echo "$dt-86400*$dd" | bc)
  dh=$(echo "$dt2/3600" | bc)
  dt3=$(echo "$dt2-3600*$dh" | bc)
  dm=$(echo "$dt3/60" | bc)
  ds=$(echo "$dt3-60*$dm" | bc)
  echo "${dd} Days ${dh} Hours ${dm} Minutes ${ds} Seconds"
}

check_java() {
  # $1 MIN_JAVA_VERSION
  # $2 MAX_JAVA_VERSION
  min_version="$1"
  max_version="$2"
  if [ -z "${1}" ] || [ -z "${2}" ]; then
    err "[check_java] Set min and max java version."
  fi
  if type -p java >/dev/null; then
    _java=java
  elif [[ -n "$JAVA_HOME" ]] && [[ -x "$JAVA_HOME/bin/java" ]]; then
    _java="$JAVA_HOME/bin/java"
  else
    dependency_not_found "Java is not installed or not in PATH."
  fi

  if [[ "$_java" ]]; then
    version=$("$_java" -version 2>&1 | awk -F '"' '/version/ {print $2}')
  fi
  min_version=$(version_comparison "$version" $MIN_JAVA_VERSION)
  max_version=$(version_comparison "$version" $MAX_JAVA_VERSION)

  if [ "$min_version" = ">" ]; then
    if [ "$max_version" = "<" ]; then
      dependency_found "Java $version"
      return
    fi
  fi
  dependency_not_found "Current Java $version not sufficient. Needed Java version: $MIN_JAVA_VERSION"
}

check_maven() {
  if type -p mvn >/dev/null; then
    dependency_found "Maven"
  else
    dependency_not_found "Maven"
  fi
}

check_program_installed() {
  # $1 Programms name
  if type -p $1 >/dev/null; then
    dependency_found "$1"
  else
    dependency_not_found "$1"
  fi
}

check_mandatory_argument() {
  # If $2 is set it is used as a value for $1. Else $3 is used as a default value.
  # If neither $2 nor $3 is set, an error is thrown.
  # $1 Name of the variable
  # $2 Value of the variable
  # $3 Optional default value
  if [ -z "${2}" ]; then
    if [ -n "${3}" ]; then
      say "${UNDERLINE_TEXT}Setting default variable${END_CUSTOM_SYNTAX} $1=$3"
      export "${1}"="${3}"
    else
      err "$1 needs to be set."
    fi
  else
    say "${UNDERLINE_TEXT}Setting custom variable${END_CUSTOM_SYNTAX} $1=$2"
  fi
}

GetAbsoluteParentPath() {
  # Get the absolute parent path for a file or folder
  # Example ./your/path/test.txt -> /absolut/your/path/
  # Example ./your/path/ -> /absolut/your/
  VAR=$1
  dirname "${VAR}"
}

CheckWriteAccess() {
  # Check if the script user has write access to a specific folder
  # $1 the folder
  local input_folder=$1
  if [[ -d "$input_folder" ]] && >>$input_folder/temp.txt; then
    say "$input_folder found and the current user has write access."
    rm "$input_folder/temp.txt"
  else
    err "Please make sure the current user has write access for $input_folder."
  fi
}

CheckNonRoot() {
  if [ $(id -u) == 0 ]; then
    err "Don't run this script as root"
  fi
}

CheckLinuxSystem() {
  if [[ "$OSTYPE" != "linux-gnu"* ]] && [[ "$OSTYPE" != "darwin"* ]]; then
    err "This script only runs in linux and Mac OS systems"
  fi
}

# Check for deps
check_program_installed curl
check_program_installed jo
check_program_installed bc

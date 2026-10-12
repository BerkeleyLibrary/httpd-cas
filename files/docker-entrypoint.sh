#!/bin/sh
set -e

# Source defaults so Apache can expand the CAS environment variables.
. /usr/local/bin/pre-init/50-cas-variables.sh

exec "$@"

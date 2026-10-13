#!/bin/bash

app_url="localhost:8080"
cas_login="Location: https://auth.berkeley.edu/cas/"

# Restricted per metadata (dct_accessRights_s) and public (legacy dc_rights_s)
restricted_map="/maps/berkeley-s7c980"
public_map="/maps/berkeley-s76m41"

function check {
  local desc="$1"; shift
  if "$@"; then
    echo "PASS: ${desc}"
  else
    echo "FAILED: ${desc}"
    return 1
  fi
}

function status_is {
  [ "$(curl -s -o /dev/null -w '%{http_code}' "${app_url}$1")" = "$2" ]
}

function redirects_to_cas {
  curl -sI "${app_url}$1" | grep -q "${cas_login}"
}

function lists {
  curl -s "${app_url}$1" | grep -q "href=\"$2\""
}

function test_public {
  check "/public/ serves custom dynamic index page" \
    sh -c "curl -s '${app_url}/public/' | grep -q 'The Regents of the University of California'"
}

function test_ucb {
  check "/UCB/ redirects to auth.berkeley.edu" redirects_to_cas /UCB/
}

function test_maps {
  local rc=0
  check "/maps/ lists maps"                      lists /maps/ berkeley-s7c980/                     || rc=1
  check "restricted map: metadata is public"     status_is "${restricted_map}/metadata/geoblacklight.json" 200 || rc=1
  check "restricted map: data/ listing is public" lists "${restricted_map}/data/" original/          || rc=1
  check "restricted map: nested listing shows files" lists "${restricted_map}/data/original/" data.zip || rc=1
  check "restricted map: data file requires CAS" redirects_to_cas "${restricted_map}/data/original/data.zip" || rc=1
  check "restricted map: MultiViews can't bypass CAS" redirects_to_cas "${restricted_map}/data/original/data" || rc=1
  check "public map: data file is served"        status_is "${public_map}/data/original/data.zip" 200 || rc=1
  check "public map: repeat request (cached) is served" status_is "${public_map}/data/original/data.zip" 200 || rc=1
  check "unknown map: data path requires CAS"    redirects_to_cas "/maps/nonexistent/data/x.zip"   || rc=1
  return $rc
}

function test_map_access_unit {
  # Run as www-data (like httpd does) so permission tests aren't skipped for root.
  if docker compose run --rm --no-deps -T -u www-data -v "$PWD/test:/test:ro" app \
      python3 -m unittest discover -s /test/unit; then
    echo "PASS: map-access.py unit tests"
  else
    echo "FAILED: map-access.py unit tests"
    return 1
  fi
}

function run_tests {
  local rc=0
  test_public || rc=1
  test_ucb || rc=1
  test_maps || rc=1
  test_map_access_unit || rc=1
  return $rc
}

function stackup {
  docker compose up -d --build > /dev/null 2>&1
  sleep 3
}

function stackdown {
  docker compose down -v --remove-orphans > /dev/null 2>&1
}

function main {
  trap stackdown EXIT
  stackup
  run_tests || exit 1
}

main

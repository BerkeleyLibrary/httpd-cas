#!/bin/bash

app_url="localhost:8080"

function test_public {
  if curl -s "${app_url}/public/" | grep -q 'The Regents of the University of California'; then
    echo "PASS: /public/ serves custom dynamic index page"
  else
    echo "FAILED: /public/ serves custom dynamic index page"
    return 1
  fi
}

function test_ucb {
  if curl -sI "${app_url}/UCB/" | grep -q "Location: https://auth.berkeley.edu/cas/"; then
    echo "PASS: /UCB/ redirects to auth.berkeley.edu"
  else
    echo "FAILED: /UCB/ redirects to auth.berkeley.edu"
    return 1
  fi
}

function run_tests {
  test_public &
  test1=$!
  test_ucb &
  test2=$!

  wait $test1
  res1=$?
  wait $test2
  res2=$?

  [ "$res1" -eq "0" -a "$res2" -eq "0" ] || exit 1
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
  run_tests
}

main

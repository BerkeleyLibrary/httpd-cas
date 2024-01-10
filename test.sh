#!/bin/sh -e

function cleanup {
  docker compose down -v --remove-orphans > /dev/null 2>&1
}
trap cleanup EXIT

cleanup
docker compose up -d --build > /dev/null 2>&1
sleep 3

curl -s localhost/public/ | grep -q sample1.txt
echo "PASS: /public/ does not require authentication"

curl -sI localhost/UCB/ | grep -q 'Location: https://auth.berkeley.edu/cas/?service=http%3a%2f%2flocalhost%2fUCB%2f'
echo "PASS: /UCB/ requires CASAuth"

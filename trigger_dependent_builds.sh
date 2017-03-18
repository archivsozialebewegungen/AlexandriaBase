#!/bin/sh

body='{
"request": {
  "branch":"master"
}}'

curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Travis-API-Version: 3" \
  -H "Authorization: token ${AUTH_TOKEN}" \
  -d "$body" \
  https://api.travis-ci.org/repo/archivsozialebewegungen%2FAlexandriaGui/requests

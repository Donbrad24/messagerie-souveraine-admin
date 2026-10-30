#!/bin/bash
# Révocation immédiate d'un agent.
# Usage : ADMIN_TOKEN=... ./revoquer.sh nom.utilisateur
set -e
if [ -z "$1" ] || [ -z "$ADMIN_TOKEN" ]; then
  echo "Usage : ADMIN_TOKEN=<jeton> $0 <nom.utilisateur>"
  exit 1
fi
USER_ID="@$1:localhost"
curl -s -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"erase": false}' \
  "http://localhost:8008/_synapse/admin/v1/deactivate/$USER_ID"
echo
echo "Agent $USER_ID révoqué."

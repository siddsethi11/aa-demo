#!/bin/sh
set -eu

KONNECT_API_URL="${KONNECT_API_URL:-https://us.api.konghq.com}"
if [ -z "${KONNECT_TOKEN:-}" ]; then
  echo "KONNECT_TOKEN is required" >&2
  exit 1
fi

if [ ! -f /certs/tls.crt ]; then
  echo "Missing /certs/tls.crt" >&2
  exit 1
fi

token=$(printf "%s" "$KONNECT_TOKEN" | tr -d '"')

cp_id="${KONNECT_CP_ID:-}"
if [ -z "$cp_id" ]; then
  if [ -z "${KONNECT_CONTROL_PLANE_NAME:-}" ]; then
    echo "Set KONNECT_CP_ID or KONNECT_CONTROL_PLANE_NAME" >&2
    exit 1
  fi

  encoded_name=$(jq -nr --arg v "$KONNECT_CONTROL_PLANE_NAME" '$v|@uri')

  cp_json=$(curl -sS \
    -H "Authorization: Bearer $token" \
    "$KONNECT_API_URL/v2/control-planes?filter%5Bname%5D%5Beq%5D=$encoded_name")

  cp_id=$(printf "%s" "$cp_json" | jq -r '.data[0].id // empty')
  if [ -z "$cp_id" ]; then
    echo "Could not resolve control plane id for '$KONNECT_CONTROL_PLANE_NAME'" >&2
    exit 1
  fi
fi

cert_payload=$(jq -Rs '{cert: .}' /certs/tls.crt)
list_json=$(curl -sS \
  -H "Authorization: Bearer $token" \
  "$KONNECT_API_URL/v2/control-planes/$cp_id/dp-client-certificates")

exists=$(printf "%s" "$list_json" | jq -r --rawfile cert /certs/tls.crt '
  [(.items // [])[] | .cert] | any(. == $cert)
')

if [ "$exists" = "true" ]; then
  echo "DP cert already registered in Konnect control plane $cp_id"
  exit 0
fi

http_code=$(curl -sS -o /tmp/konnect_dp_cert_create.json -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer $token" \
  -H "Content-Type: application/json" \
  "$KONNECT_API_URL/v2/control-planes/$cp_id/dp-client-certificates" \
  --data "$cert_payload")

if [ "$http_code" = "201" ] || [ "$http_code" = "200" ]; then
  echo "Registered DP cert in Konnect control plane $cp_id"
  exit 0
fi

echo "Failed to register DP cert (HTTP $http_code)" >&2
cat /tmp/konnect_dp_cert_create.json >&2
exit 1

#!/bin/bash
# Atualiza o DDNS (DuckDNS) com o IP público atual deste host.
# O token real fica em ~/valheim/.env (DUCKDNS_TOKEN); nao hardcodar aqui.
if [[ -f "$HOME/valheim/.env" ]]; then
  set -a
  source "$HOME/valheim/.env"
  set +a
fi
TOKEN="${DUCKDNS_TOKEN:?defina DUCKDNS_TOKEN no ~/valheim/.env}"
DOMAIN="mundovanir"

curl -sS -o /dev/null -w "%{http_code}\n" "https://www.duckdns.org/update?domains=$DOMAIN&token=$TOKEN&ip="

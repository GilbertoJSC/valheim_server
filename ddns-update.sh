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

# IPv4 (força IPv4 para garantir)
curl -4 -sS -o /dev/null -w "ipv4:%{http_code}\n" "https://www.duckdns.org/update?domains=$DOMAIN&token=$TOKEN&ip=&verbose=true" || echo "ipv4: falha"

# IPv6 (se host tem IPv6, atualiza; senão ignora)
curl -6 -sS -o /dev/null -w "ipv6:%{http_code}\n" "https://www.duckdns.org/update?domains=$DOMAIN&token=$TOKEN&ipv6=&verbose=true" 2>/dev/null || echo "ipv6: sem conectividade ou não configurado"

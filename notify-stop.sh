#!/bin/bash
# Notifica no Discord que o servidor parou.
# Chamado via ExecStopPost do valheim.service.
set -u
"$HOME/valheim/discord-notify.sh" --title "MundoVanir offline" --color 15548997 \
  --footer "Valheim • mundovanir.duckdns.org" \
  --field "Endereço (DDNS)|mundovanir.duckdns.org" \
  "Servidor Valheim foi parado."

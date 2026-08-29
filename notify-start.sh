#!/bin/bash
# Notifica no Discord que o servidor subiu (com join code e IP).
# Chamado via ExecStartPost do valheim.service.
set -u
sleep 30
LOG=$(journalctl --user -u valheim.service -n 300 --no-pager 2>/dev/null)
CODE=$(echo "$LOG" | grep -oE 'join code [0-9]+' | grep -oE '[0-9]+' | tail -1)
if [[ -n "$CODE" ]]; then
  "$HOME/valheim/discord-notify.sh" --title "O servidor está online" --color 5763719 \
    --desc "Servidor Valheim iniciado, já pode jogar o joguinho." \
    --footer " • Valheim • Odin won't save you here..." \
    --field "Join code|$CODE" --field "Endereço|mundovanir.duckdns.org:2456"
else
  "$HOME/valheim/discord-notify.sh" --title "O servidor está online" --color 5763719 \
    --desc "Servidor Valheim foi iniciado, mas o join code não foi encontrado." \
    --footer " • Valheim • Odin won't save you here..." \

fi

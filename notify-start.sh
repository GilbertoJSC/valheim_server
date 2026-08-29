#!/bin/bash
# Notifica no Discord que o servidor subiu (com join code e IP).
# Chamado via ExecStartPost do valheim.service.
set -u
sleep 30
LOG=$(journalctl --user -u valheim.service -n 300 --no-pager 2>/dev/null)
CODE=$(echo "$LOG" | grep -oE 'join code [0-9]+' | grep -oE '[0-9]+' | tail -1)
IP=$(echo "$LOG" | grep -oE 'and IP [0-9.]+' | grep -oE '[0-9.]+' | tail -1)
if [[ -n "$CODE" ]]; then
  "$HOME/valheim/discord-notify.sh" --title "MundoVanir online" --color 5763719 \
    --footer "Valheim • ${IP:-?}" \
    --field "Join code|$CODE" --field "IP:Porta|${IP:-?}:2456" \
    "Servidor Valheim iniciado."
else
  "$HOME/valheim/discord-notify.sh" --title "MundoVanir online" --color 5763719 \
    --footer "Valheim" "Servidor Valheim iniciado (join code nao encontrado no log)."
fi

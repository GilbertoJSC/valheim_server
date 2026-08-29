#!/bin/bash
# Notifica no Discord que o servidor parou.
# Chamado via ExecStopPost do valheim.service.
set -u
"$HOME/valheim/discord-notify.sh" --title "O servidor está offline" --color 15548997 \
  --footer " • Valheim • Odin won't save you here..." \
  --desc "Servidor Valheim foi parado para atualizações."

#!/bin/bash
# Atualiza o Valheim server via SteamCMD e reinicia o serviço.
# Notifica o Discord em cada etapa.
set -u
"$HOME/valheim/discord-notify.sh" --title "Valheim atualizando" --color 16776960 \
  "Aplicando update via SteamCMD..."

"$HOME/steamcmd/steamcmd.sh" +login anonymous \
  +force_install_dir "$HOME/valheim" +app_update 896660 validate +quit

systemctl --user restart valheim.service

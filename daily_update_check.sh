#!/bin/bash
# Verifica diariamente se há atualização do Valheim Dedicated Server e aplica se houver.
# Roda via systemd timer às 03:00. Só reinicia se houve download.
set -u
LOG=/tmp/valheim_daily_update.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Verificando atualização Valheim..."
timeout 120 ~/steamcmd/steamcmd.sh +login anonymous +force_install_dir ~/valheim +app_update 896660 validate +quit > "$LOG" 2>&1
cat "$LOG"
if grep -q "Success! App '896660' fully installed" "$LOG"; then
  if grep -q "downloading" "$LOG"; then
    echo "Atualização detectada e aplicada, reiniciando valheim.service"
    ~/valheim/discord-notify.sh --title "Valheim atualizado" --color 5763719 --desc "Atualização diária aplicada via SteamCMD. Reiniciando servidor..." --footer "SteamCMD • $(date '+%Y-%m-%d %H:%M')" || true
    systemctl --user restart valheim.service
  else
    echo "Já está atualizado (sem download), sem restart"
  fi
else
  echo "Falha ao verificar/atualizar (sem Success)"
  cat "$LOG" | tail -n 20
fi
rm -f "$LOG"

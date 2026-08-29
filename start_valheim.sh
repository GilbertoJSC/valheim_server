#!/bin/bash
# Copia editavel de start_server.sh (nao e sobrescrita pelo Steam).
# Steam (Linux) precisa do LD_LIBRARY_PATH apontando para ./linux64.
export LD_LIBRARY_PATH=./linux64:$LD_LIBRARY_PATH
export SteamAppId=892970

# Carrega segredos do .env (senha do servidor), se existir
if [[ -f "$HOME/valheim/.env" ]]; then
  set -a
  source "$HOME/valheim/.env"
  set +a
fi

NAME="MundoVanir"
WORLD="MundoVanir"
PASSWORD="${VALHEIM_PASSWORD:?defina VALHEIM_PASSWORD no ~/valheim/.env}"
PORT=2456
SAVEDIR="$HOME/valheim/saves"

mkdir -p "$SAVEDIR"

# === Parâmetros opcionais ===
# Preset (-preset): perfil completo de modifiers.
#   Valores: normal, casual, easy, hard, hardcore, immersive, hammer
PRESET="casual"
# World modifier (-modifier <nome> <valor>): ajusta uma regra por vez.
#   combat:       veryeasy, easy, hard, veryhard
#   deathpenalty: casual, veryeasy, easy, hard, hardcore
#   resources:    muchless, less, more, muchmore, most
#   raids:        none, muchless, less, more, muchmore
#   portals:      casual, hard, veryhard
# -modifier combat hard
# -modifier resources more
# Setkey (-setkey <chave>): liga/desliga uma regra.
#   nobuildcost, passivemobs, nomap, playerevents
# -setkey nobuildcost
#
# Backups rotativos:
# -saveinterval 1800 -backups 4 -backupshort 7200 -backuplong 43200
#
# Outros:
# -instanceid "1"   # vários servidores na mesma porta/MAC
# -logFile "$SAVEDIR/valheim.log"

./valheim_server.x86_64 \
  -nographics -batchmode \
  -name "$NAME" \
  -port $PORT \
  -world "$WORLD" \
  -password "$PASSWORD" \
  -public 0 \
  -preset "$PRESET" \
  -crossplay \
  -savedir "$SAVEDIR"

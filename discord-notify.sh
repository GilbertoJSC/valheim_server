#!/bin/bash
# discord-notify.sh — envia mensagens para um canal Discord via Incoming Webhook.
# Config: DISCORD_WEBHOOK_URL em ~/valheim/.env (ou env).
# Uso:
#   discord-notify.sh "mensagem simples"
#   discord-notify.sh --title "T" --desc "D" --color 5763719 \
#     --field "Join code|123456" --footer "Valheim" "texto"
set -euo pipefail

ENV_FILE="${VALHEIM_ENV:-$HOME/valheim/.env}"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"
[[ -z "$WEBHOOK_URL" ]] && { echo "DISCORD_WEBHOOK_URL não definida" >&2; exit 1; }

TITLE=""; DESC=""; COLOR=""; PLAIN=0
FOOTER=""; TS=""; THUMB=""; URL=""; AUTHOR=""
FIELDS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) TITLE="$2"; shift 2;;
    --desc|--description) DESC="$2"; shift 2;;
    --color) COLOR="$2"; shift 2;;
    --field) FIELDS+=("$2"); shift 2;;
    --footer) FOOTER="$2"; shift 2;;
    --timestamp) TS="$2"; shift 2;;
    --thumbnail) THUMB="$2"; shift 2;;
    --url) URL="$2"; shift 2;;
    --author) AUTHOR="$2"; shift 2;;
    --plain) PLAIN=1; shift;;
    --help|-h) echo "uso: $0 [opções] <mensagem>"; exit 0;;
    *) break;;
  esac
done
MSG="${*:-}"

[[ -z "$MSG" && -z "$TITLE" && -z "$DESC" ]] && { echo "mensagem vazia" >&2; exit 1; }

JSON="$(python3 - "$MSG" "$TITLE" "$DESC" "$COLOR" "$PLAIN" "$FOOTER" "$TS" "$THUMB" "$URL" "$AUTHOR" "${FIELDS[@]}" <<'PY'
import json, sys, datetime
msg, title, desc, color, plain, footer, ts, thumb, url, author = sys.argv[1:11]
fields = sys.argv[11:]
emb = {}
if color:
    emb["color"] = int(color)
if title:
    emb["title"] = title
if desc:
    emb["description"] = desc
if not title and not desc:
    emb["description"] = msg
if url:
    emb["url"] = url
if thumb:
    emb["thumbnail"] = {"url": thumb}
if author:
    emb["author"] = {"name": author}
if footer:
    emb["footer"] = {"text": footer}
if ts:
    emb["timestamp"] = ts
elif title or desc or fields:
    emb["timestamp"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
if fields:
    emb["fields"] = [{"name": f.split("|", 1)[0], "value": f.split("|", 1)[1], "inline": True}
                     for f in fields if "|" in f]
if plain == "1" or (not title and not desc and not fields):
    payload = {"content": msg}
else:
    payload = {"embeds": [emb]}
print(json.dumps(payload))
PY
)"

curl -sS -H "Content-Type: application/json" \
  -H "User-Agent: ValheimBot (valheim, 1.0)" \
  -X POST "$WEBHOOK_URL" -d "$JSON"
echo

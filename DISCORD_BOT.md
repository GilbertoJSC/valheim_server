# Discord Bot (comandos `/server`, `/players`)

O webhook (`discord-notify.sh`) é **one-way** (servidor → Discord). Para comandos
interativos como `/server` e `/players` é necessário um **bot** (Application + Bot
token + conexão Gateway). O bot roda como systemd user service no host.

## Pré-requisitos (Discord Developer Portal)

1. https://discord.com/developers/applications → **New Application**.
2. Aba **Bot** → **Reset Token / Copy** → esse é o `DISCORD_BOT_TOKEN`.
3. Aba **OAuth2 → URL Generator**:
   - Scopes: `bot` + `applications.commands`
   - Bot Permissions: `Send Messages`, `Use Slash Commands`
   - Abra a URL gerada e convide o bot para o seu servidor.
4. Anote o **Server/Guild ID** (botão direito no servidor → Copiar ID) para
   `DISCORD_GUILD_ID` (comandos aparecem na hora; sem ele, levam até 1h).

## Configuração (no servidor)

Adicione ao `~/valheim/.env` (já fora do repo via `.gitignore`):

```
DISCORD_BOT_TOKEN=seu_token
DISCORD_GUILD_ID=seu_guild_id       # opcional (comandos instantâneos)
DISCORD_CHANNEL_ID=seu_channel_id   # opcional (restringe a 1 canal)
```

## Restrição a um canal específico

O bot é convidado para o **servidor inteiro**, mas a interação pode ser limitada
a um único canal definindo `DISCORD_CHANNEL_ID` (Botão direito no canal →
*Copiar ID do Canal*). Com isso, `/server` e `/players` só respondem naquele
canal; em outros canais o bot avisa (mensagem efêmera) onde usar. Sem a variável,
funciona em qualquer canal. Combine com permissões do Discord (negar "Usar
Comandos de Aplicação" nos demais canais) para reforço.

## Arquivos

- `valheim-bot.py` — bot (discord.py). Comandos:
  - `/server` → nome, mundo, status, join code e parâmetros rodando (com `-password` mascarado).
  - `/players` → SteamIDs detectados no log desde o último start (**best-effort**;
    o dedicado vanilla não expõe API de jogadores, então pode ser incompleto).
- `valheim-bot.service` — systemd user service.

## Setup no servidor

```bash
python3 -m pip install --user -r ~/valheim/requirements.txt
cp ~/valheim/valheim-bot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now valheim-bot.service
journalctl --user -u valheim-bot.service -f   # verificar login + sync
```

## Notas

- O bot coexiste com o webhook: webhook = notificações push; bot = comandos.
- Sem `DISCORD_BOT_TOKEN` o bot não sobe (`SystemExit`).
- Para parar: `systemctl --user stop valheim-bot.service`.

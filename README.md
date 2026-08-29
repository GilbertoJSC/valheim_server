# Valheim Dedicated Server — 192.168.3.6

Servidor dedicado Valheim rodando em `192.168.3.6` (LAN). Jogadores na mesma
rede entram em **Join IP → `192.168.3.6:2456`** (senha definida em `.env` → `VALHEIM_PASSWORD`).

Host: Nobara Linux 44 (base Fedora, KDE), x86_64. Usuário: `gilberto`.
Deploy via systemd **user service** (sem root).

## Estrutura no servidor

| Caminho | Conteúdo |
| --- | --- |
| `~/steamcmd` | SteamCMD (instalado via tarball) |
| `~/valheim` | Valheim Dedicated Server (app Steam `896660`) |
| `~/valheim/start_valheim.sh` | Script de start (cópia editável, **não** sobrescrita pelo Steam) |
| `~/valheim/saves` | Mundos (`.db`/`.fwl`) + `adminlist.txt` |
| `~/.config/systemd/user/valheim.service` | Service systemd de usuário |

## Comandos no servidor (via SSH)

Conectar:
```
ssh -i ~/.ssh/valheim_server gilberto@192.168.3.6
```

Gerenciar o serviço:
```
systemctl --user start valheim.service
systemctl --user stop valheim.service
systemctl --user status valheim.service --no-pager
journalctl --user -u valheim.service -f
```

Iniciar sozinho após reboot (precisa de sudo uma vez):
```
sudo loginctl enable-linger gilberto
systemctl --user enable valheim.service
```

Atualizar o servidor (SteamCMD + notificação Discord):
```
~/valheim/update_valheim.sh
```
(Ou manual: `~/steamcmd/steamcmd.sh +login anonymous +force_install_dir ~/valheim +app_update 896660 validate +quit` e `systemctl --user restart valheim.service`.)

## Firewall (firewalld)

O firewalld já libera `1025-65535/udp` neste host, então a LAN passa. Regra
explícita (idempotente):
```
sudo firewall-cmd --add-port=2456-2458/udp --permanent
sudo firewall-cmd --reload
```
Como é IP interno (192.168.x.x), **não** é necessário port forwarding nem IP público.

## Argumentos do servidor (`start_valheim.sh`)

Parâmetros detalhados e obrigatórios (LD_LIBRARY_PATH, SteamAppId) em
[SERVER_PARAMS.md](SERVER_PARAMS.md).

`-nographics -batchmode -name MundoVanir -port 2456 -world MundoVanir`
`-password "$VALHEIM_PASSWORD" -public 0 -crossplay -savedir ~/valheim/saves`

- `-public 0`: não listado (só conexão direta por IP ou join code).
- `-crossplay`: backend PlayFab (Steam + Xbox/Game Pass); join via código, sem
  port forwarding. Funciona no Linux (confirmado). Veja seção Crossplay.
- `-savedir` aponta para `~/valheim/saves` para facilitar backup.

## Administração do servidor

(Fonte: `Valheim Dedicated Server Manual.pdf` no servidor.)

### Listas de controle (`~/valheim/saves`)

Adicione **um Platform User ID por linha** (case-sensitive):

- `adminlist.txt` — admins (kick/ban/save, comandos F5).
- `bannedlist.txt` — banidos.
- `permittedlist.txt` — whitelist: se preenchida, **bane todos os demais**.

O Platform User ID vem do log do servidor ou do painel **F2** no jogo, no formato
`[Platform]_[User ID]` (ex.: `Steam_7656...`). **Não** é o SteamID64 puro.

### Comandos de admin no jogo (F5)

```
kick <nome>      # expulsa
ban <nome>       # bane
unban <nome>     # desbane
banned           # lista banidos
```

### Parar o servidor

Sempre pare de forma limpa para não deixar processo órfão:
- Via systemd: `systemctl --user stop valheim.service`.
- Script direto no terminal: **CTRL+C** (nunca feche a janela pelo X).

### Pacotes Linux necessários

O dedicado precisa de `libatomic1`, `libpulse0`, `libpulse-dev`. O host Nobara já
os tem; anotados para reinstalações.

### Docker (opcional)

Exige GLIBC_2.29 / GLIBCXX_3.4.26; se a distro for mais antiga, use
`docker_start_server.sh` (volume `valheim_server_data`). Não usado neste host.

## DDNS (acesso externo via IPv4)

O IP público é dinâmico, então usamos DuckDNS. Domínio: `mundovanir.duckdns.org`
(→ IP público atual, ex.: `<ip-publico-dinamico>`).

- Atualizador: `~/valheim/ddns-update.sh` (token real só no servidor).
- Timer systemd de usuário: `ddns-update.timer` roda a cada 5 min
  (`systemctl --user status ddns-update.timer`).
- Testar manual: `systemctl --user start ddns-update.service`.

Como o cliente do Valheim tem bugs conhecidos de join via IPv6, o caminho de
acesso externo via IP é **IPv4 + port forwarding**, não IPv6 direto.

### Crossplay (ativo como stopgap — sem port forwarding)

O `start_valheim.sh` tem `-crossplay`, então o servidor usa o relay **PlayFab**
e jogadores externos entram **via join code, sem precisar abrir portas no roteador**.
Funcionou no Linux (sem erro PlayFab conhecido).

- Join code: aparece no log a cada start e **muda toda vez que o serviço reinicia**:
  `journalctl --user -u valheim.service -n 50 --no-pager | grep -i 'join code'`
- Conexão: no Valheim → Join Game → informe o **join code** (ou cole
  `steam://run/%2Bconnect%20<ip>:2456`). Senha definida em `.env` (`VALHEIM_PASSWORD`).
- Quando o port forwarding do roteador estiver pronto, remova `-crossplay` do
  script para voltar ao modo IP direto (`mundovanir.duckdns.org:2456`).

### Port forwarding ainda necessário (no roteador 192.168.3.1)

O DDNS só mapeia nome→IP. Para jogadores externos via IPv4, crie no roteador:

| Porta | Protocolo | Destino |
| --- | --- | --- |
| 2456-2458 | UDP | 192.168.3.6 |

Sem isso, só a LAN e clientes IPv6 diretos conseguem conectar.

## Seed do mundo (MundoVanir)

- Seed aplicada: **`AoTxSDA2wJ`** (mundo `MundoVanir`).
- O servidor dedicado vanilla **não aceita seed por linha de comando** — a seed é
  definida na criação do mundo. Procedimento usado: gerou-se o mundo no cliente
  Steam com essa seed, e subiu-se o par `.db`/`.fwl` para
  `~/valheim/saves/worlds_local/` (os arquivos vieram da Steam Cloud:
  `Steam/userdata/<id>/892970/remote/worlds/`).
- Para recriar esse mundo do zero com a mesma seed, basta o `.fwl` (guarda nome+seed).

## Backup

Antes de atualizações (Valheim 1.0 / Deep North em 09/09/2026), copie os
arquivos `.db` e `.fwl` de `~/valheim/saves`.

## Notificações Discord

O servidor avisa mudanças de estado num canal específico via **Incoming
Webhook** (sem bot, sem auth).

- **Config:** `~/valheim/.env` no servidor, com `DISCORD_WEBHOOK_URL`. Template em
  `.env.example`; o `.env` real está no `.gitignore` (segredo — nunca no repo).
- **Script:** `discord-notify.sh` — texto simples
  (`./discord-notify.sh "mensagem"`) ou embed com flags
  `--title/--desc/--color/--field "Nome|Valor"/--footer/--timestamp/--thumbnail/--url/--author`
  (ex.: `./discord-notify.sh --title "T" --color 5763719 --footer "Valheim" --field "Join code|123456" "texto"`).
  `--timestamp` é automático em embeds.
- **Modelos prontos** (online/offline/update/manutenção/IP/backup, com todos os
  campos do embed): `discord-templates.md`.
- **Wire no systemd:** `ExecStartPost` (online + join code + IP, após ~25s) e
  `ExecStopPost` (offline) em `valheim.service`. Opcional: notificar após
  `app_update` (via `update_valheim.sh`).
- Endpoint usado: `POST https://discord.com/api/v10/webhooks/{id}/{token}`.
  Pelo menos `content` ou `embeds` obrigatório; `content` ≤ 2000 chars.

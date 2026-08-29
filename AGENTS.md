# AGENTS.md

Repo de config/deploy do **Valheim Dedicated Server** hospedado em
`192.168.3.6` (LAN). O repo guarda os scripts/serviço; o jogo roda no host.

## Project

- Valheim dedicated server (Steam app `896660`) em `192.168.3.6`.
- Host: Nobara Linux 44 (Fedora-based, KDE), x86_64, usuário `gilberto`.
- Deploy via **systemd user service** (sem root). SteamCMD em `~/steamcmd`,
  server em `~/valheim`, saves em `~/valheim/saves`.
- Acesso ao host: `ssh -i ~/.ssh/valheim_server gilberto@192.168.3.6`.

## Developer / ops commands (no servidor)

- Subir/parar/log: `systemctl --user start|stop|status valheim.service`,
  `journalctl --user -u valheim.service -f`.
- Atualizar server: `~/steamcmd/steamcmd.sh +login anonymous +force_install_dir ~/valheim +app_update 896660 validate +quit` e `systemctl --user restart valheim.service`.
- Autostart no boot: `sudo loginctl enable-linger gilberto` + `systemctl --user enable valheim.service`.
- DDNS (IPv4 dinâmico): `~/valheim/ddns-update.sh` + `ddns-update.timer` (DuckDNS, `mundovanir.duckdns.org` → IP público). Token só no servidor, não no repo.

## Architecture / conventions

- `start_valheim.sh` é uma CÓPIA editável de `start_server.sh` do Steam — o
  original é sobrescrito a cada update, nunca edite o original.
- `start_valheim.sh` precisa de `LD_LIBRARY_PATH=./linux64` e `SteamAppId=892970`.
- `-crossplay` está ATIVO (stopgap): relay PlayFab, join via código, sem
  port forwarding. Join code aparece no log e muda a cada restart. Remover a
  flag quando o port forwarding do roteador estiver pronto.
- Jogadores conectam em `192.168.3.6:2456`; senha definida em `.env` (`VALHEIM_PASSWORD`).

## Conventions

- Editar sempre os arquivos do repo e subir via `scp` para o host (o heredoc
  do PowerShell corrompe `$HOME`/quebras de linha — prefira `scp`).
- Firewall do host já libera `1025-65535/udp`; regra explícita
  `2456-2458/udp` é idempotente.
- `sudo` de `gilberto` é NOPASSWD (arquivo `/etc/sudoers.d/gilberto`).
- Backup de `.db`/`.fwl` em `~/valheim/saves` antes de updates (1.0 em 09/09/2026).
- Nunca reiniciar nem parar o `valheim.service` sem perguntar ao usuário antes (mesmo
  que seja para aplicar uma configuração já aprovada).
- Sugerir mensagem de commit (conventional commits) em toda alteração.

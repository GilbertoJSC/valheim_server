#!/usr/bin/env python3
"""Valheim Discord bot.

Comandos slash:
  /server  -> nome, join code, parâmetros rodando e status
  /players -> jogadores online (best-effort via log)

Config (~/valheim/.env):
  DISCORD_BOT_TOKEN  (obrigatório)
  DISCORD_GUILD_ID   (opcional; comando aparece na hora se definido)
"""
import os
import re
import shlex
import subprocess
from pathlib import Path

import discord
from discord import app_commands

ENV_PATH = Path.home() / "valheim" / ".env"
VALHEIM_DIR = Path.home() / "valheim"
START_SCRIPT = VALHEIM_DIR / "start_valheim.sh"
SERVICE = "valheim.service"


def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            s = re.sub(r"^export\s+", "", s, flags=re.I)
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = load_env(ENV_PATH)
TOKEN = ENV.get("DISCORD_BOT_TOKEN") or os.environ.get("DISCORD_BOT_TOKEN")
_gid = (ENV.get("DISCORD_GUILD_ID") or os.environ.get("DISCORD_GUILD_ID")
        or ENV.get("DISCORD_SERVER_ID") or os.environ.get("DISCORD_SERVER_ID"))
GUILD = int(_gid) if _gid else None

_cid = (ENV.get("DISCORD_VALHEIM_CHANNEL_ID") or os.environ.get("DISCORD_VALHEIM_CHANNEL_ID")
        or ENV.get("DISCORD_CHANNEL_ID") or os.environ.get("DISCORD_CHANNEL_ID"))
ALLOWED_CHANNEL = int(_cid) if _cid else None

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def run(cmd: str, timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except Exception as e:  # noqa: BLE001
        return f"(erro ao executar: {e})"


def service_status() -> str:
    return (run(f"systemctl --user is-active {SERVICE}").strip() or "unknown")


def journal(n: int = 120) -> str:
    return run(f"journalctl --user -u {SERVICE} -n {n} --no-pager", timeout=20)


def get_name_world() -> tuple:
    name = world = "?"
    if START_SCRIPT.exists():
        txt = START_SCRIPT.read_text()
        m = re.search(r'^\s*NAME="?([^"\n]+)"?', txt, re.M)
        if m:
            name = m.group(1)
        m = re.search(r'^\s*WORLD="?([^"\n]+)"?', txt, re.M)
        if m:
            world = m.group(1)
    return name, world


def get_join_code() -> str:
    codes = re.findall(r'join code (\d+)', journal(150))
    return codes[-1] if codes else None


def get_live_cmdline() -> str:
    out = run("pgrep -af valheim_server.x86_64", timeout=10)
    for line in out.splitlines():
        if "valheim_server" in line:
            return line.split(None, 1)[-1] if " " in line else line
    return None


PARAM_DOCS = {
    "-name": "Nome do servidor exibido na lista de servidores.",
    "-world": "Mundo carregado (arquivos <nome>.db/.fwl em savedir/worlds_local).",
    "-password": "Senha de acesso a partida.",
    "-port": "Porta UDP base (2456=servico, 2457=status, 2458=Valheim+).",
    "-public": "Visibilidade: 0 = nao listado, 1 = listado publicamente.",
    "-crossplay": "Crossplay via relay PlayFab (entra por codigo, sem port forwarding).",
    "-savedir": "Diretorio de saves e mundos.",
    "-preset": "Preset de dificuldade (normal/casual/easy/hard/hardcore/immersive/hammer).",
    "-modifier": "Modificador individual (combate/morte/recursos/raids/portais).",
    "-setkey": "Chave de mundo/ceno (seed custom ou devcommands).",
    "-backups": "Backups automaticos do mundo.",
    "-backupinterval": "Intervalo do backup em minutos.",
    "-backupshort": "Retencao de backups curtos (minutos).",
    "-backuplong": "Retencao de backups longos (minutos).",
    "-savedelay": "Intervalo de autosave em segundos.",
    "-logFile": "Arquivo de log do servidor.",
    "-instanceid": "ID de instancia (rodar multiplos servidores).",
    "-batchmode": "Modo headless (sem interface grafica).",
    "-nographics": "Nao inicializa graficos (modo servidor).",
}


def format_server_params() -> str:
    cmd = get_live_cmdline()
    src = cmd or (START_SCRIPT.read_text().replace("\\\n", " ") if START_SCRIPT.exists() else "")
    if not src:
        return "(indisponivel)"
    try:
        toks = shlex.split(src, comments=False, posix=True)
    except Exception:  # noqa: BLE001
        toks = src.split()
    pairs, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t.startswith("-"):
            if i + 1 < len(toks) and not toks[i + 1].startswith("-"):
                pairs.append((t, toks[i + 1]))
                i += 2
                continue
            pairs.append((t, ""))
        i += 1
    if not pairs:
        return "(nenhum parametro reconhecido)"
    lines = []
    for flag, val in pairs:
        if flag in ("-password", "--password"):
            val = "<segredo>"
        desc = PARAM_DOCS.get(flag, "Parametro da linha de comando do Valheim.")
        shown = " ".join(p for p in (flag, val) if p)
        lines.append(f"`{shown}` — {desc}")
    return "\n".join(lines)


def get_players() -> list:
    """Best-effort: SteamIDs de jogadores no log desde o último start."""
    players = []
    for m in re.finditer(r'Player\s+(\d{6,})', journal(500)):
        pid = m.group(1)
        if pid not in players:
            players.append(pid)
    return players


@client.event
async def on_ready():
    print(f"[bot] logado como {client.user}", flush=True)
    if GUILD:
        guild = discord.Object(id=GUILD)
        try:
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
            print(f"[bot] comandos slash sincronizados no guild {GUILD}", flush=True)
        except Exception as e:
            print(f"[bot] AVISO: falha ao sincronizar no guild ({e}); usando comandos globais", flush=True)
            await tree.sync()
    else:
        await tree.sync()
        print("[bot] comandos slash globais sincronizados (pode levar ate 1h)", flush=True)
    print("[bot] pronto.", flush=True)


async def ensure_channel(interaction: discord.Interaction) -> bool:
    """Restringe os comandos a um canal especifico (DISCORD_CHANNEL_ID)."""
    if ALLOWED_CHANNEL and interaction.channel_id != ALLOWED_CHANNEL:
        await interaction.response.send_message(
            f"Comando disponivel apenas no canal <#{ALLOWED_CHANNEL}>.", ephemeral=True
        )
        return False
    await interaction.response.defer()
    return True


@tree.command(name="server", description="Mostra informacoes do servidor Valheim")
async def cmd_server(interaction: discord.Interaction):
    if not await ensure_channel(interaction):
        return
    _, world = get_name_world()
    status = service_status()
    if status != "active":
        embed = discord.Embed(
            title="⚔️ Valheim Server 🛡️",
            description="Servidor offline no momento. 💤",
            color=0xED4245,
        )
        embed.add_field(name="Mundo 🌍", value=world, inline=True)
        embed.add_field(name="Status 📶", value=status, inline=True)
        embed.set_footer(text=f"valheim-bot • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        await interaction.followup.send(embed=embed)
        return
    code = get_join_code()
    embed = discord.Embed(title="⚔️ Valheim Server 🛡️", color=0x57C7E9)
    embed.add_field(name="Mundo 🌍", value=world, inline=True)
    embed.add_field(name="Status 📶", value=status, inline=True)
    embed.add_field(name="Join code 🔑", value=code or "indisponivel", inline=True)
    embed.add_field(name="Parâmetros ⚙️", value=format_server_params(), inline=False)
    embed.set_footer(text=f"valheim-bot • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    await interaction.followup.send(embed=embed)


@tree.command(name="status", description="Status do servidor: online/offline, endereço, join code e jogadores")
async def cmd_status(interaction: discord.Interaction):
    if not await ensure_channel(interaction):
        return
    _, world = get_name_world()
    status = service_status()
    if status != "active":
        embed = discord.Embed(
            title="⚔️ Valheim Server 🛡️",
            description="Servidor offline no momento. 💤",
            color=0xED4245,
        )
        embed.add_field(name="Mundo 🌍", value=world, inline=True)
        embed.add_field(name="Status 📶", value=status, inline=True)
        embed.set_footer(text=f"valheim-bot • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        await interaction.followup.send(embed=embed)
        return
    code = get_join_code()
    players = get_players()
    embed = discord.Embed(
        title="⚔️ Valheim Server 🛡️",
        description="Servidor online! 🟢 Que os deuses te guiem! 🐺",
        color=0x57C7E9,
    )
    embed.add_field(name="Endereço 📡", value="mundovanir.duckdns.org:2456", inline=True)
    embed.add_field(name="Mundo 🌍", value=world, inline=True)
    embed.add_field(name="Join code 🔑", value=code or "indisponivel", inline=True)
    if players:
        embed.add_field(name="Vikings em Valhalla 🪓", value="\n".join(players), inline=False)
    else:
        embed.add_field(name="Valhalla 🏚️", value="Não tem ninguém em casa. Os corvos de Odin vigiam sozinhos... 🐦‍⬛", inline=False)
    embed.set_footer(text=f"valheim-bot • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    await interaction.followup.send(embed=embed)


@tree.command(name="players", description="Lista jogadores online (best-effort)")
async def cmd_players(interaction: discord.Interaction):
    if not await ensure_channel(interaction):
        return
    players = get_players()
    if not players:
        await interaction.followup.send("Nenhum viking à vista... O salão está vazio. 🏚️ (best-effort)")
        return
    embed = discord.Embed(
        title="🪓 Vikings em Valhalla 🛡️",
        color=0x57C7E9,
        description="Detectados no log desde o ultimo start. Pode ser incompleto. 🐺",
    )
    embed.add_field(name="SteamIDs 🆔", value="\n".join(players), inline=False)
    await interaction.followup.send(embed=embed)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN nao definido em ~/valheim/.env")
    client.run(TOKEN)

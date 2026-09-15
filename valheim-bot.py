#!/usr/bin/env python3
"""Valheim Discord bot.

Comandos slash:
  /server  -> nome, join code, parâmetros rodando e status
  /players -> jogadores online (best-effort via log)
  /status  -> online/offline, endereço, join code e jogadores
  /update  -> verifica build e aplica atualização via SteamCMD (para/reinicia o servidor)
  /wiki    -> busca item na wiki (resumo + receita + links)
  /seed    -> seed do mundo + link do mapa interativo
  /food    -> stats de comida (vida/fôlego/eitr/duração + receita)
  /help    -> lista os comandos do bot

Config (~/valheim/.env):
  DISCORD_BOT_TOKEN  (obrigatório)
  DISCORD_GUILD_ID   (opcional; comando aparece na hora se definido)
"""
import asyncio
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
APP_ID = "896660"
STEAMCMD = Path.home() / "steamcmd" / "steamcmd.sh"
APP_MANIFEST = VALHEIM_DIR / "steamapps" / f"appmanifest_{APP_ID}.acf"
WIKI_API = "https://valheim.fandom.com/api.php"
WIKI_PAGE = "https://valheim.fandom.com/wiki"
WIKI_GG = "https://valheim.wiki.gg/wiki"
VALHEIM_TOOLS = "https://www.valheim.tools/items"


def vt_slug(title: str) -> str:
    """Slug do valheim.tools: minúsculas, espaços -> hífens, só [a-z0-9-]."""
    import unicodedata
    s = unicodedata.normalize("NFKD", title.lower()).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-{2,}", "-", s)
WIKI_UA = "ValheimBot/1.0 (Discord bot; admin mundovanir)"


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


def get_installed_buildid() -> str | None:
    """Build instalado (appmanifest do SteamCMD)."""
    try:
        if APP_MANIFEST.exists():
            m = re.search(r'"buildid"\s+"(\d+)"', APP_MANIFEST.read_text())
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def get_latest_buildid(timeout: int = 30) -> str | None:
    """Build público mais recente via api.steamcmd.net (com fallback p/ steamcmd)."""
    import json
    import urllib.request
    try:
        req = urllib.request.Request(
            f"https://api.steamcmd.net/v1/info/{APP_ID}",
            headers={"User-Agent": "ValheimBot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        app = (data.get("data") or {}).get(APP_ID) or {}
        branches = ((app.get("depots") or {}).get("branches") or {})
        public = branches.get("public") or {}
        if public.get("buildid"):
            return str(public["buildid"])
    except Exception:
        pass
    out = run(
        f"timeout {timeout} {STEAMCMD} +login anonymous +app_info_update 1 "
        f"+app_info_print {APP_ID} +quit",
        timeout=timeout + 10,
    )
    m = re.search(r'"public"\s*\{\s*"buildid"\s*"(\d+)"', out)
    if m:
        return m.group(1)
    return None


def get_players() -> list:
    """Best-effort: jogadores online via log (nomes de personagem, fallback SteamID)."""
    text = journal(800)
    names: list[str] = []
    for m in re.finditer(r'Got character ZDOID from\s+([^\n:]+?)\s*:', text):
        n = m.group(1).strip().strip('"').strip("'")
        if n and n not in names:
            names.append(n)
    if names:
        counts = re.findall(r'now\s+(\d+)\s+player\(s\)', text)
        if counts:
            try:
                cur = int(counts[-1])
                if cur == 0:
                    return []
                if len(names) > cur:
                    return names[-cur:]
            except Exception:
                pass
        return names
    steam: list[str] = []
    for m in re.finditer(r'Steam_(\d+)', text):
        sid = m.group(1)
        if sid not in steam:
            steam.append(sid)
    if steam:
        counts = re.findall(r'now\s+(\d+)\s+player\(s\)', text)
        if counts:
            try:
                cur = int(counts[-1])
                if cur == 0:
                    return []
                if len(steam) > cur:
                    return steam[-cur:]
            except Exception:
                pass
        return steam
    return []


def wiki_api(params: dict, timeout: int = 20) -> dict | list | None:
    """GET na API MediaWiki da Fandom (a wiki.gg oficial bloqueia bots com 401)."""
    import json
    import urllib.parse
    import urllib.request
    try:
        req = urllib.request.Request(
            f"{WIKI_API}?{urllib.parse.urlencode(params)}",
            headers={"User-Agent": WIKI_UA},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None


def _strip_wiki(text: str) -> str:
    """Remove templates/links/negrito do wikitext para texto puro."""
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"\[\[([^|\]#]+)\|([^]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^]]+)\]\]", r"\1", text)
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [ln for ln in text.splitlines() if ln.strip() not in ("*", "-", "•", "")]
    return "\n".join(lines).strip()


def wiki_lookup(query: str) -> dict | None:
    """Busca item na wiki (Fandom; wiki.gg bloqueia bots): resumo + receita + links."""
    import urllib.parse
    q = (query or "").strip()
    if not q:
        return None
    found = wiki_api({"action": "opensearch", "search": q, "limit": 5, "format": "json"})
    titles: list[str] = []
    if isinstance(found, list) and len(found) >= 2 and isinstance(found[1], list):
        titles = [t for t in found[1] if t]
    if not titles:
        sr = wiki_api(
            {"action": "query", "list": "search", "srsearch": q, "srlimit": 5, "format": "json"}
        )
        try:
            titles = [r["title"] for r in sr["query"]["search"]]
        except Exception:
            titles = []
    words = [w for w in q.lower().split() if w]
    title = next(
        (t for t in titles
         if t.lower() == q.lower() or all(w in t.lower() for w in words)),
        None,
    )
    if not title:
        return None
    wt = wiki_api(
        {"action": "query", "prop": "revisions|info", "titles": title, "redirects": 1,
         "rvprop": "content", "rvslots": "main", "inprop": "url", "format": "json"}
    )
    try:
        pages = (wt or {}).get("query", {}).get("pages", {})
        page = next(iter(pages.values()))
        if "missing" in page:
            return None
        rev = page["revisions"][0]["slots"]["main"]["*"]
    except Exception:
        return None
    real_title = page.get("title") or title
    thumb = None
    m_img = re.search(r"\|\s*image\s*=\s*([^\n|]+)", rev)
    if m_img and m_img.group(1).strip():
        fn = m_img.group(1).strip()
        thumb = (f"{WIKI_PAGE}/Special:FilePath/"
                 f"{urllib.parse.quote(fn.replace(' ', '_'), safe='')}"
                 "?width=400")
    body = rev.split("}}", 1)[-1] if "}}" in rev else rev
    summary = _strip_wiki(body.split("==", 1)[0])
    if len(summary) > 900:
        cut = summary[:900]
        summary = cut[: cut.rfind(".") + 1 or 900]
    mats: list[tuple[str, str]] = []
    m_mat = re.search(r"\|\s*materials\s*1\s*=(.*?)(?:\n\||\n\}\}|\Z)", rev, re.S)
    if m_mat:
        for line in m_mat.group(1).splitlines():
            lm = re.search(r"\[\[([^|\]#]+)(?:\|[^]]*)?\]\]\s*[x×]?\s*(\d+)?", line)
            if not lm:
                continue
            name = lm.group(1).strip()
            if not name or ":" in name:
                continue
            if name not in [n for n, _ in mats]:
                mats.append((name, lm.group(2) or ""))
    return {
        "title": real_title,
        "summary": summary,
        "url": page.get("fullurl") or f"{WIKI_PAGE}/{real_title.replace(' ', '_')}",
        "thumb": thumb,
        "materials": mats,
        "gg_url": f"{WIKI_GG}/{urllib.parse.quote(real_title.replace(' ', '_'), safe='')}",
        "vt_url": f"{VALHEIM_TOOLS}/{vt_slug(real_title)}",
    }


def get_world_seed() -> tuple[str | None, str]:
    """Seed do mundo atual lida do .fwl (formato: \\n<nome>\\n<seed>)."""
    _, world = get_name_world()
    if not world or world == "?":
        return None, "?"
    base = VALHEIM_DIR / "saves" / "worlds_local"
    cands: list[tuple[int, float, Path]] = []
    try:
        for p in base.glob(f"{world}.fwl*"):
            if p.is_file():
                cands.append((0, -p.stat().st_mtime, p))
        for p in sorted(base.glob(f"{world}_backup_*.fwl"),
                        key=lambda q: q.stat().st_mtime, reverse=True):
            if p.is_file():
                cands.append((2, -p.stat().st_mtime, p))
        for p in sorted((base / world).glob("_main.*.fwl2"),
                        key=lambda q: q.stat().st_mtime, reverse=True):
            if p.is_file():
                cands.append((1, -p.stat().st_mtime, p))
    except OSError:
        pass
    for _, _, p in sorted(cands):
        try:
            txt = p.read_bytes().decode("latin-1")
        except OSError:
            continue
        m = re.search("\n" + re.escape(world) + r"\n([A-Za-z0-9]+)", txt)
        if m:
            return m.group(1), world
    return None, world


def _wiki_resolve(query: str) -> str | None:
    """Resolve o título da página (opensearch + fallback fulltext, com guarda)."""
    q = (query or "").strip()
    if not q:
        return None
    found = wiki_api({"action": "opensearch", "search": q, "limit": 5, "format": "json"})
    titles: list[str] = []
    if isinstance(found, list) and len(found) >= 2 and isinstance(found[1], list):
        titles = [t for t in found[1] if t]
    if not titles:
        sr = wiki_api(
            {"action": "query", "list": "search", "srsearch": q, "srlimit": 5, "format": "json"}
        )
        try:
            titles = [r["title"] for r in sr["query"]["search"]]
        except Exception:
            titles = []
    words = [w for w in q.lower().split() if w]
    return next(
        (t for t in titles
         if t.lower() == q.lower() or all(w in t.lower() for w in words)),
        None,
    )


def _wiki_revision(title: str) -> tuple[str | None, str | None, str | None]:
    """Retorna (wikitexto, título real, url) ou (None, None, None)."""
    wt = wiki_api(
        {"action": "query", "prop": "revisions|info", "titles": title, "redirects": 1,
         "rvprop": "content", "rvslots": "main", "inprop": "url", "format": "json"}
    )
    try:
        pages = (wt or {}).get("query", {}).get("pages", {})
        page = next(iter(pages.values()))
        if "missing" in page:
            return None, None, None
        rev = page["revisions"][0]["slots"]["main"]["*"]
        real = page.get("title") or title
        url = page.get("fullurl") or f"{WIKI_PAGE}/{real.replace(' ', '_')}"
        return rev, real, url
    except Exception:
        return None, None, None


def _wiki_thumb(rev: str) -> str | None:
    m_img = re.search(r"\|\s*image\s*=\s*([^\n|]+)", rev)
    if m_img and m_img.group(1).strip():
        import urllib.parse
        fn = m_img.group(1).strip()
        return (f"{WIKI_PAGE}/Special:FilePath/"
                f"{urllib.parse.quote(fn.replace(' ', '_'), safe='')}"
                "?width=400")
    return None


def _wiki_links(real: str, fandom_url: str) -> tuple[str, str, str]:
    import urllib.parse
    gg = f"{WIKI_GG}/{urllib.parse.quote(real.replace(' ', '_'), safe='')}"
    vt = f"{VALHEIM_TOOLS}/{vt_slug(real)}"
    return gg, vt, fandom_url


def food_lookup(query: str) -> dict | None:
    """Stats de comida via Fandom: vida/fôlego/eitr/duração/regen + receita."""
    import urllib.parse
    title = _wiki_resolve(query)
    if not title:
        return None
    rev, real, url = _wiki_revision(title)
    if rev is None:
        return None
    def field(name: str) -> str:
        m = re.search(r"\|\s*" + name + r"\s*=\s*([^\n|]*)", rev)
        return m.group(1).strip().rstrip("}") if m else ""
    if "food" not in field("type").lower():
        gg, vt, _ = _wiki_links(real, url)
        return {"title": real, "url": url, "gg_url": gg, "vt_url": vt, "is_food": False}
    health, stamina = field("health"), field("stamina")
    dur = field("duration")
    dur_txt = f"{int(dur) // 60} min" if dur.isdigit() else dur
    mats: list[tuple[str, str]] = []
    m_mat = re.search(r"\|\s*materials\s*=(.*?)(?:\n\||\n\}\}|\Z)", rev, re.S)
    if m_mat:
        for line in m_mat.group(1).splitlines():
            lm = re.search(r"\[\[([^|\]#]+)(?:\|[^]]*)?\]\]\s*[x×]?\s*(\d+)?", line)
            if not lm:
                continue
            name = lm.group(1).strip()
            if not name or ":" in name:
                continue
            if name not in [n for n, _ in mats]:
                mats.append((name, lm.group(2) or ""))
    gg, vt, _ = _wiki_links(real, url)
    station = re.sub(r"\[\[([^|\]]+)(?:\|[^]]+)?\]\]", r"\1", field("source"))
    return {"title": real, "url": url, "gg_url": gg, "vt_url": vt, "is_food": True,
            "desc": field("description"), "health": health, "stamina": stamina,
            "eitr": field("eitr"), "duration": dur_txt, "regen": field("healing"),
            "effect": field("effect"), "station": station,
            "thumb": _wiki_thumb(rev), "materials": mats}


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
        embed.set_footer(text=f"Buri • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        await interaction.followup.send(embed=embed)
        return
    code = get_join_code()
    embed = discord.Embed(title="⚔️ Valheim Server 🛡️", color=0x57C7E9)
    embed.add_field(name="Mundo 🌍", value=world, inline=True)
    embed.add_field(name="Status 📶", value=status, inline=True)
    embed.add_field(name="Join code 🔑", value=code or "indisponivel", inline=True)
    embed.add_field(name="Parâmetros ⚙️", value=format_server_params(), inline=False)
    embed.set_footer(text=f"Buri • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
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
        embed.set_footer(text=f"Buri • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        await interaction.followup.send(embed=embed)
        return
    code = get_join_code()
    players = get_players()
    embed = discord.Embed(
        title="⚔️ Valheim Server 🛡️",
        description="Servidor online! Odin won't save you here...! 🐺",
        color=0x57C7E9,
    )
    embed.add_field(name="Endereço 📡", value="mundovanir.duckdns.org:2456", inline=True)
    embed.add_field(name="Mundo 🌍", value=world, inline=True)
    embed.add_field(name="Join code 🔑", value=code or "indisponivel", inline=True)
    if players:
        embed.add_field(name="Vikings em Valhalla 🪓", value="\n".join(players), inline=False)
    else:
        embed.add_field(name="Valhalla 🏚️", value="Não tem ninguém em casa. Os corvos de Odin vigiam sozinhos... 🐦‍⬛", inline=False)
    embed.set_footer(text=f"Buri • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    await interaction.followup.send(embed=embed)


@tree.command(name="players", description="Lista jogadores online")
async def cmd_players(interaction: discord.Interaction):
    if not await ensure_channel(interaction):
        return
    players = get_players()
    if not players:
        await interaction.followup.send("Nenhum viking à vista... O salão está vazio.")
        return
    embed = discord.Embed(
        title="🪓 Vikings em Valhalla 🛡️",
        color=0x57C7E9
    )
    embed.add_field(name="SteamIDs 🆔", value="\n".join(players), inline=False)
    await interaction.followup.send(embed=embed)


@tree.command(name="update", description="Verifica se há atualização do servidor e aplica se houver")
async def cmd_update(interaction: discord.Interaction):
    if not await ensure_channel(interaction):
        return
    installed = get_installed_buildid()
    await interaction.followup.send(
        f"🔍 Verificando atualização... (instalado: `{installed or 'desconhecido'}`)"
    )
    latest = await asyncio.to_thread(get_latest_buildid)
    if not latest:
        await interaction.followup.send(
            "⚠️ Não consegui consultar o build mais recente (api.steamcmd.net/steamcmd). Tente de novo em alguns minutos."
        )
        return
    if installed and installed == latest:
        embed = discord.Embed(
            title="⚔️ Valheim Server 🛡️",
            description=f"✅ Já está atualizado! Build `{installed}`. 🎉",
            color=0x57F287,
        )
        embed.set_footer(text=f"Buri • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        await interaction.followup.send(embed=embed)
        return
    await interaction.followup.send(
        f"⬇️ Atualização encontrada: `{installed or '?'} → {latest}`. "
        "Parando o servidor e aplicando via SteamCMD... ⏳"
    )
    stop_out = await asyncio.to_thread(run, f"systemctl --user stop {SERVICE}", 60)
    upd_out = await asyncio.to_thread(
        run,
        f"{STEAMCMD} +login anonymous +force_install_dir {VALHEIM_DIR} "
        f"+app_update {APP_ID} validate +quit",
        1500,
    )
    ok = f"Success! App '{APP_ID}' fully installed" in upd_out
    downloaded = "downloading" in upd_out.lower() or "staging" in upd_out.lower()
    await asyncio.to_thread(run, f"systemctl --user start {SERVICE}", 60)
    new_installed = get_installed_buildid()
    if ok:
        await asyncio.sleep(25)
        code = get_join_code()
        embed = discord.Embed(
            title="⚔️ Valheim Server 🛡️",
            description=(
                f"✅ Atualizado de `{installed or '?'} → {new_installed or latest}`! 🎉\n"
                + ("📦 Download aplicado." if downloaded else "📦 Arquivos validados.")
                + (f"\n🔑 Join code: `{code}`" if code else "")
            ),
            color=0x57F287,
        )
    else:
        embed = discord.Embed(
            title="⚔️ Valheim Server 🛡️",
            description=(
                "❌ Falha ao aplicar a atualização via SteamCMD. "
                f"(instalado: `{new_installed or installed or '?'}` | remoto: `{latest}`)\n"
                f"```{upd_out[-1500:]}```"
            ),
            color=0xED4245,
        )
    embed.set_footer(text=f"Buri • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    await interaction.followup.send(embed=embed)


@tree.command(name="wiki", description="Busca um item na wiki de Valheim (resumo + receita)")
@app_commands.describe(item="Nome do item (ex.: bronze axe, smelter, iron sword)")
async def cmd_wiki(interaction: discord.Interaction, item: str):
    if not await ensure_channel(interaction):
        return
    q = (item or "").strip()
    if not q:
        await interaction.followup.send("Informe o nome do item. Ex.: `/wiki item:bronze axe` 📖")
        return
    await interaction.followup.send(f"🔍 Consultando a wiki por `{q}`... 📖")
    info = await asyncio.to_thread(wiki_lookup, q)
    if not info:
        await interaction.followup.send(
            f"❌ Não encontrei `{q}` na wiki. Tente o nome em inglês "
            "(ex.: `bronze axe`, `smelter`, `iron sword`)."
        )
        return
    summary = info["summary"] or "(sem resumo na wiki)"
    if len(summary) > 1500:
        cut = summary[:1500]
        summary = cut[: cut.rfind(".") + 1 or 1500]
    import urllib.parse
    if info["materials"]:
        lines = []
        for n, qty in info["materials"][:8]:
            link = f"{WIKI_PAGE}/{urllib.parse.quote(n.replace(' ', '_'), safe='')}"
            lines.append(f"• [{n}]({link})" + (f" x{qty}" if qty else ""))
        recipe = "\n".join(lines)
    else:
        recipe = "(receita não identificada — ver seção Crafting na wiki)"
    embed = discord.Embed(
        title=f"📖 {info['title']} ⚔️",
        url=info["vt_url"],
        description=summary,
        color=0x57C7E9,
    )
    if info["thumb"]:
        embed.set_thumbnail(url=info["thumb"])
    embed.add_field(name="🛠️ Receita/Materiais", value=recipe[:1024], inline=False)
    embed.add_field(
        name="🔗 Links",
        value=f"[Valheim.tools]({info['vt_url']}) • [Fandom]({info['url']}) • [Wiki oficial]({info['gg_url']})",
        inline=False,
    )
    embed.set_footer(text=f"Buri • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    await interaction.followup.send(embed=embed)


@tree.command(name="seed", description="Mostra a seed do mundo e o link do mapa interativo")
async def cmd_seed(interaction: discord.Interaction):
    if not await ensure_channel(interaction):
        return
    seed, world = await asyncio.to_thread(get_world_seed)
    if not seed:
        await interaction.followup.send(
            f"❌ Não consegui ler a seed do mundo `{world}` no `.fwl`. 🗺️"
        )
        return
    url = f"https://www.valheim.tools/seed-map?seed={seed}"
    embed = discord.Embed(
        title="🗺️ Seed do Mundo 🧭",
        description="Veja terreno, biomas, altares, traders e pontos de interesse do nosso mundo no valheim.tools.",
        color=0x57C7E9,
    )
    embed.add_field(name="Mundo 🌍", value=world, inline=True)
    embed.add_field(name="Seed 🌱", value=f"`{seed}`", inline=True)
    embed.add_field(name="🗺️ Mapa interativo", value=f"[Abrir seed map]({url})", inline=False)
    embed.set_footer(text=f"Buri • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    await interaction.followup.send(embed=embed)


@tree.command(name="food", description="Stats de uma comida (vida, fôlego, duração + receita)")
@app_commands.describe(comida="Nome da comida (ex.: deer stew, honey, bread)")
async def cmd_food(interaction: discord.Interaction, comida: str):
    if not await ensure_channel(interaction):
        return
    q = (comida or "").strip()
    if not q:
        await interaction.followup.send("Informe a comida. Ex.: `/food comida:deer stew` 🍖")
        return
    await interaction.followup.send(f"🔍 Consultando a cozinha por `{q}`... 🍲")
    info = await asyncio.to_thread(food_lookup, q)
    if not info:
        await interaction.followup.send(
            f"❌ Não encontrei `{q}` na wiki. Tente o nome em inglês "
            "(ex.: `deer stew`, `honey`, `bread`)."
        )
        return
    if not info.get("is_food"):
        await interaction.followup.send(
            f"⚠️ `{info['title']}` não parece ser comida (sem stats). "
            f"Tente `/wiki item:{q}` 📖 ou veja em {info['url']}"
        )
        return
    import urllib.parse
    embed = discord.Embed(
        title=f"🍖 {info['title']} 🍲",
        url=info["url"],
        description=info["desc"] or "Comida valheimiana! 😋",
        color=0x57C7E9,
    )
    if info["thumb"]:
        embed.set_thumbnail(url=info["thumb"])
    embed.add_field(name="❤️ Vida", value=info["health"] or "-", inline=True)
    embed.add_field(name="🍗 Fôlego", value=info["stamina"] or "-", inline=True)
    if info["eitr"]:
        embed.add_field(name="✨ Eitr", value=info["eitr"], inline=True)
    embed.add_field(name="⏱️ Duração", value=info["duration"] or "-", inline=True)
    if info["regen"]:
        embed.add_field(name="💚 Regen", value=info["regen"], inline=True)
    if info["station"]:
        embed.add_field(name="🏭 Estação", value=info["station"], inline=True)
    if info["materials"]:
        lines = []
        for n, qty in info["materials"][:8]:
            link = f"{WIKI_PAGE}/{urllib.parse.quote(n.replace(' ', '_'), safe='')}"
            lines.append(f"• [{n}]({link})" + (f" x{qty}" if qty else ""))
        embed.add_field(name="🛠️ Receita", value="\n".join(lines)[:1024], inline=False)
    if info["effect"]:
        embed.add_field(name="✨ Efeito", value=info["effect"][:1024], inline=False)
    embed.add_field(
        name="🔗 Links",
        value=f"[Valheim.tools]({info['vt_url']}) • [Fandom]({info['url']}) • [Wiki oficial]({info['gg_url']})",
        inline=False,
    )
    embed.set_footer(text=f"Buri • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    await interaction.followup.send(embed=embed)


@tree.command(name="help", description="Lista os comandos do Buri")
async def cmd_help(interaction: discord.Interaction):
    if not await ensure_channel(interaction):
        return
    embed = discord.Embed(
        title="🐺 Buri — Comandos ⚔️",
        description="Guardião do MundoVanir! Skål! 🍻",
        color=0x57C7E9,
    )
    embed.add_field(
        name="📜 Comandos",
        value=(
            "**/server** 🖥️ — info do servidor + parâmetros\n"
            "**/status** 📡 — online/offline, endereço, join code e jogadores\n"
            "**/players** 🪓 — vikings online agora\n"
            "**/update** ⬇️ — verifica e aplica atualização (reinicia o servidor!)\n"
            "**/wiki** 📖 — `/wiki item:bronze axe` → resumo + receita + links\n"
            "**/food** 🍖 — `/food comida:deer stew` → stats da comida + receita\n"
            "**/seed** 🗺️ — seed do mundo + mapa interativo\n"
            "**/help** ❓ — esta lista"
        ),
        inline=False,
    )
    embed.set_footer(text=f"Buri • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    await interaction.followup.send(embed=embed)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN nao definido em ~/valheim/.env")
    client.run(TOKEN)

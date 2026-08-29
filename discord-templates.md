# Modelos de mensagens Discord (Valheim)

Modelos prontos para os eventos do servidor, usando `discord-notify.sh`.
Cada evento tem (1) o comando e (2) o JSON final enviado ao webhook, para
você visualizar todos os campos possíveis do **embed**.

## Campos possíveis no embed (Webhook Execute)

| Campo | Tipo | Limite | Descrição |
| --- | --- | --- | --- |
| `title` | string | 256 | Título do embed. |
| `description` | string | 4096 | Corpo de texto (markdown parcial). |
| `url` | string | — | Link clicável no título. |
| `timestamp` | ISO8601 | — | Horário (ex.: `2026-08-29T12:00:00Z`). Auto gerado se omitido. |
| `color` | inteiro | — | Cor da barra (RGB decimal). Verde `5763719`, vermelho `15548997`, amarelo `16776960`, azul `3447003`, laranja `16753920`. |
| `footer` | obj `{text, icon_url}` | text 2048 | Rodapé. |
| `thumbnail` | obj `{url}` | — | Imagem pequena à direita. |
| `image` | obj `{url}` | — | Imagem grande embaixo. |
| `author` | obj `{name, url, icon_url}` | name 256 | Cabeçalho superior. |
| `fields[]` | array | 25 itens | `{name, value, inline}`. `name` 256, `value` 1024. |
| `type` | — | — | Sempre `rich`; ignorado no envio. |

**Limites gerais:** `content` ≤ 2000 caracteres; até 10 embeds por mensagem;
~6000 caracteres no total do embed. Pelo menos `content` **ou** `embeds` obrigatório.

---

## 1. Servidor Online (join code + IP) — verde

```bash
~/valheim/discord-notify.sh --title "MundoVanir online" --color 5763719 \
  --footer "Valheim • <ip-publico>" \
  --field "Join code|367135" --field "IP:Porta|<ip-publico>:2456" \
  "Servidor Valheim iniciado."
```

```json
{
  "embeds": [{
    "title": "MundoVanir online",
    "description": "Servidor Valheim iniciado.",
    "color": 5763719,
    "footer": { "text": "Valheim • <ip-publico>" },
    "timestamp": "2026-08-29T12:00:00Z",
    "fields": [
      { "name": "Join code", "value": "367135", "inline": true },
      { "name": "IP:Porta", "value": "<ip-publico>:2456", "inline": true }
    ]
  }]
}
```

## 2. Servidor Offline — vermelho

```bash
~/valheim/discord-notify.sh --title "MundoVanir offline" --color 15548997 \
  --footer "Valheim • mundovanir.duckdns.org" --field "Endereço (DDNS)|mundovanir.duckdns.org" "Servidor Valheim foi parado."
```

```json
{
  "embeds": [{
    "title": "MundoVanir offline",
    "description": "Servidor Valheim foi parado.",
    "color": 15548997,
    "footer": { "text": "Valheim • mundovanir.duckdns.org" },
    "timestamp": "2026-08-29T12:05:00Z"
  }]
}
```

## 3. Atualização iniciada — amarelo

```bash
~/valheim/discord-notify.sh --title "Valheim atualizando" --color 16776960 \
  --footer "SteamCMD" "Aplicando update via SteamCMD..."
```

```json
{
  "embeds": [{
    "title": "Valheim atualizando",
    "description": "Aplicando update via SteamCMD...",
    "color": 16776960,
    "footer": { "text": "SteamCMD" },
    "timestamp": "2026-08-29T12:10:00Z"
  }]
}
```

## 4. Atualização concluída — verde

```bash
~/valheim/discord-notify.sh --title "Valheim atualizado" --color 5763719 \
  --footer "SteamCMD" --field "Versão|1.0.0" "Update aplicado e servidor online."
```

```json
{
  "embeds": [{
    "title": "Valheim atualizado",
    "description": "Update aplicado e servidor online.",
    "color": 5763719,
    "footer": { "text": "SteamCMD" },
    "timestamp": "2026-08-29T12:15:00Z",
    "fields": [
      { "name": "Versão", "value": "1.0.0", "inline": true }
    ]
  }]
}
```

## 5. Manutenção (aviso manual) — azul

```bash
~/valheim/discord-notify.sh --title "Manutenção agendada" --color 3447003 \
  --footer "Aviso manual" \
  --field "Início|29/08 22:00" --field "Duração|~30 min" \
  "Servidor ficará fora do ar para manutenção."
```

```json
{
  "embeds": [{
    "title": "Manutenção agendada",
    "description": "Servidor ficará fora do ar para manutenção.",
    "color": 3447003,
    "footer": { "text": "Aviso manual" },
    "timestamp": "2026-08-29T12:20:00Z",
    "fields": [
      { "name": "Início", "value": "29/08 22:00", "inline": true },
      { "name": "Duração", "value": "~30 min", "inline": true }
    ]
  }]
}
```

## 6. Mudança de IP / DDNS — laranja

```bash
~/valheim/discord-notify.sh --title "IP público alterado" --color 16753920 \
  --footer "DuckDNS" --field "Novo IP|189.28.99.200" \
  "O DDNS mundovanir.duckdns.org foi atualizado."
```

```json
{
  "embeds": [{
    "title": "IP público alterado",
    "description": "O DDNS mundovanir.duckdns.org foi atualizado.",
    "color": 16753920,
    "footer": { "text": "DuckDNS" },
    "timestamp": "2026-08-29T12:25:00Z",
    "fields": [
      { "name": "Novo IP", "value": "189.28.99.200", "inline": true }
    ]
  }]
}
```

## 7. Backup realizado — azul (opcional)

```bash
~/valheim/discord-notify.sh --title "Backup concluído" --color 3447003 \
  --footer "Valheim" --field "Arquivos|MundoVanir.db / .fwl" \
  "Backup dos saves copiado para local seguro."
```

---

## Texto simples (sem embed)

Para mensagens rápidas, sem formatação de embed:

```bash
~/valheim/discord-notify.sh --plain "Servidor reiniciado por motivo X."
```

> Dica: o `--timestamp` é automático em embeds. Para definir manualmente,
> passe ISO8601: `--timestamp "2026-08-29T12:00:00Z"`.

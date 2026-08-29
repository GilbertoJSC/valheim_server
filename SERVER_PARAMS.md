# Parâmetros de linha de comando — Valheim Dedicated Server

Comando efetivo usado em `start_valheim.sh` (host `192.168.3.6`):

```bash
export LD_LIBRARY_PATH=./linux64:$LD_LIBRARY_PATH
export SteamAppId=892970

./valheim_server.x86_64 \
  -nographics -batchmode \
  -name "MundoVanir" \
  -port 2456 \
  -world "MundoVanir" \
  -password "$VALHEIM_PASSWORD" \
  -public 0 \
  -crossplay \
  -savedir "$HOME/valheim/saves"
```

`LD_LIBRARY_PATH=./linux64` e `SteamAppId=892970` são **obrigatórios** no Linux
(a biblioteca do Steam fica em `./linux64` e o AppID do jogo é `892970`).

## Parâmetros em uso

| Parâmetro | Valor | Descrição |
| --- | --- | --- |
| `-nographics` | — | Sem interface gráfica (headless). |
| `-batchmode` | — | Modo batch (sem prompts). |
| `-name` | `MundoVanir` | Nome exibido no servidor. |
| `-port` | `2456` | Porta base UDP (usa 2456‑2458). |
| `-world` | `MundoVanir` | Nome do mundo (carrega/cria `MundoVanir.fwl`/`.db`). |
| `-password` | `<definida em .env: VALHEIM_PASSWORD>` | Senha (mín. 5 caracteres, não pode estar no `-name`). |
| `-public` | `0` | `0` = não listado (só join por IP/código); `1` = listado no browser. |
| `-crossplay` | — | Backend PlayFab: join via código, sem port forwarding. |
| `-savedir` | `~/valheim/saves` | Onde ficam mundos e listas (admin/ban/permit). |

## Outros parâmetros disponíveis

Além dos usados acima, o dedicado aceita world modifiers, presets e setkeys
(passados na mesma linha do `valheim_server.x86_64`).

### Presets — `-preset <valor>`

Aplica um perfil completo de modifiers. Valores: `normal`, `casual`, `easy`,
`hard`, `hardcore`, `immersive`, `hammer`.

#### Mapeamento preset → modifiers

Cada preset define os 5 modifiers graduados abaixo (valores em lowercase, como
usados nos flags). `normal` = todos os padrões do jogo.

| Preset | combat | deathpenalty | resources | raids | portals |
| --- | --- | --- | --- | --- | --- |
| `normal` | normal | normal | normal | normal | normal |
| `casual` | veryeasy | casual | muchmore | none | casual |
| `easy` | easy | easy | more | less | normal |
| `hard` | hard | hard | less | more | hard |
| `hardcore` | veryhard | hardcore | less | more | veryhard |
| `immersive` | hard | hard | less | more | veryhard |
| `hammer` | normal | casual | muchmore | none | casual |

- `hammer` também liga os setkeys **`nobuildcost`** + **`passivemobs`**
  (alguns guias incluem `nomap`; verifique in-game).
- `-preset` sobrescreve quaisquer `-modifier`/`-setkey` anteriores; passe os
  dials individuais **depois** do preset para ajustar por cima.
- `portals` na tabela acima mostra `normal` só para os presets `normal`/`easy`:
  isso é o **padrão** (restrição clássica, sem metais nos portais), **não** um
  valor aceito por `-modifier portals`. Os valores válidos são só
  `casual`, `hard`, `veryhard`. Para portais padrão, não passe o modifier (ou
  use o preset `normal`).

Fonte: docs de presets (XGamingServer) + discussão oficial Steam; confere com os
valores de `-modifier` listados acima.

### World modifiers — `-modifier <nome> <valor>`

Ajustam uma regra por vez. Valores válidos:

| Modifier | Valores |
| --- | --- |
| `combat` | `veryeasy`, `easy`, `hard`, `veryhard` |
| `deathpenalty` | `casual`, `veryeasy`, `easy`, `hard`, `hardcore` |
| `resources` | `muchless`, `less`, `more`, `muchmore`, `most` |
| `raids` | `none`, `muchless`, `less`, `more`, `muchmore` |
| `portals` | `casual`, `hard`, `veryhard` |

Ex.: `-modifier combat hard -modifier raids none`

### Setkeys (toggles) — `-setkey <chave>`

Ligam/desligam uma regra. Chaves documentadas oficialmente:

- `nobuildcost` — construir sem gastar recursos
- `passivemobs` — inimigos só atacam se você bater primeiro
- `nomap` — desativa mapa/minimapa
- `playerevents` — raids baseadas no progresso individual de cada jogador

(Chaves como `noportals`/`teleportall` circulam em fóruns mas não constam do
guia oficial da Iron Gate; `portals` é controlado via `-modifier portals`.)

### Backups rotativos

| Parâmetro | Padrão | Descrição |
| --- | --- | --- |
| `-saveinterval <seg>` | `1800` | Intervalo de auto-save. |
| `-backups <n>` | `4` | Quantidade de backups mantidos. |
| `-backupshort <seg>` | `7200` | Intervalo do 1º backup (2h). |
| `-backuplong <seg>` | `43200` | Intervalo dos demais (12h). |

### Outros

- `-instanceid <id>` — ID único ao rodar vários servidores na mesma porta/MAC.
- `-logFile <caminho>` — redireciona o log para um arquivo (ex.: `-logFile ~/valheim/saves/valheim.log`).
- **Portas:** o manual cita default `2456-2457` (porta e porta+1). Abrimos
  `2456-2458/udp` no firewall por segurança. Com `-crossplay` o relay PlayFab
  dispensa port forwarding.

### Ordem de leitura

O servidor lê os argumentos **na ordem**: `-preset` primeiro, depois
`-modifier` e `-setkey` (assim os dials individuais sobrescrevem o preset).

---

Fonte: `Valheim Dedicated Server Manual.pdf` (Steam), presente em
`~/valheim/` no servidor. Parâmetros `-preset`/`-modifier`/`-setkey` e backups
conferem com o manual.

## Observações

- **Seed não é flag.** O servidor dedicado vanilla não aceita `-seed`/`-worldseed`.
  A seed `AoTxSDA2wJ` está gravada no `MundoVanir.fwl` (mundo gerado no cliente
  com essa seed e subido para `~/valheim/saves/worlds_local/`).
- **World modifiers / setkeys** (ex.: `-setkey nobuildcost`, `-modifier combat hard`,
  `-preset hammer`) e backup (`-saveinterval`, `-backups`, `-backupshort`,
  `-backuplong`) veja o `README.md`.
- Edite sempre `start_valheim.sh` (cópia), nunca o `start_server.sh` original
  do Steam — ele é sobrescrito a cada update.

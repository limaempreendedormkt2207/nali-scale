# Vídeo motion — Como funcionam os agentes de IA da Nali (15s)

Vídeo vertical 1080×1920 (Reels/TikTok/Shorts), 30 fps, com trilha sintetizada sincronizada com a animação.

**Saída:** `out/agentes-nali-15s.mp4`

## Roteiro

| Tempo | Cena | Texto na tela |
|---|---|---|
| 0–2,4s | Gancho | "Como funcionam os nossos AGENTES DE IA." |
| 2,4–4,5s | Entrada | "Você envia o briefing." — o card do briefing é digitado e absorvido pelo núcleo do agente |
| 4,5–10,8s | Ciclo do agente | 01 Pesquisa → 02 Criação → 03 Execução → 04 Análise (cada etapa acende no diagrama) |
| 10,8–12,2s | Loop | "E recomeça. 24/7, mais afiado a cada rodada." |
| 12,2–15s | Assinatura | NALI SCALE — "Menos achismo. Mais escala." |

## Como editar e renderizar de novo

- **Textos e etapas:** em `index.html`, edite `CAPS` (título, frase e chips de cada etapa), `NAMES` (rótulos do diagrama) e o HTML do gancho, do card de briefing e do encerramento.
- **Tempos:** objeto `T` em `index.html`. Se mudar os tempos, ajuste os mesmos marcos em `audio.mjs`.
- **Cores:** variáveis `--lime`, `--violet` e `--bg` no topo do CSS (os hex também aparecem nos atributos SVG).
- **Pré-visualizar no navegador:** abra `index.html?play` (toca em loop, em tempo real).

```bash
node audio.mjs     # gera out/trilha.wav
node render.mjs    # renderiza os 450 quadros com Playwright/Chromium e codifica com ffmpeg
node preview.mjs 1.5 5.6 13   # salva quadros soltos em out/preview/ para conferir
```

Requer Node 18+, `playwright` (com Chromium) e `ffmpeg`. As fontes (Sora e JetBrains Mono, licença OFL) estão em `fonts/`.

#!/usr/bin/env python3
"""Monta os 3 vídeos de direct response da Homa Institute.

Layout 1080x1920: filmagem no topo (recorte 720x760 da fonte, sem as legendas
antigas), faixa verde da marca embaixo com legenda palavra a palavra, cartelas
finais do próprio cliente em tela cheia.

Uso: python3 render_homa.py <v1|v2|v3|all> [--preview]
Espera em ./src os vídeos-fonte, em ./nar as narrações v1.mp3..v3.mp3 e em
./words.json os timestamps por palavra das falas (faster-whisper).
"""
import difflib
import json
import os
import re
import subprocess
import sys
import unicodedata

from PIL import Image, ImageDraw, ImageFont

FPS = 30
W, H = 1080, 1920
PANEL_H = 1140            # altura da filmagem no topo
CROP_W, CROP_H = 720, 760  # recorte na fonte 720x1280
FONT = "/usr/share/fonts/truetype/higgsfield/Montserrat-ExtraBold.ttf"
GREEN_TOP, GREEN_BOT = (22, 61, 49), (13, 37, 30)
GOLD = (214, 182, 118)
CREAM = (244, 236, 220)
WORK = "work"

# ---------------------------------------------------------------- falas (cortes)
# (fonte, entrada, saída, legenda corrigida)
BITES = {
    "VIT_A": ("vitorio", 2.58, 7.12, "Tem muita gente que reclama: tô tomando, mas não tenho tanto resultado."),
    "VIT_B": ("vitorio", 9.18, 14.40, "Reclama que fiquei uma semana inteira sem comer nada e não perdi peso."),
    "VIT_C": ("vitorio", 47.36, 58.25, "Tem pessoas que estão com uma certa idade, ou muito inflamadas, o metabolismo está lentíssimo. Por isso que a pessoa fica sem comer, mas não perde peso: porque a roda está parada."),
    "VIT_D": ("vitorio", 101.60, 110.00, "Passar com médico, ter uma consulta, ter um acompanhamento, tá? E fazer certinho. Porque aí sim você vai ter resultados, não vai perder músculo."),
    "JU_A": ("ju", 0.74, 6.95, "Quer três motivos de verdade para você emagrecer? E nenhum deles é sobre ficar mais bonita."),
    "JU_B": ("ju", 46.98, 52.10, "Você não precisa esperar ficar doente para começar a cuidar da sua saúde."),
    "JU_C": ("ju", 52.82, 62.95, "Emagrecer não é sobre ser magra, é sobre chegar aos 50, 60, 70 anos com independência, força e qualidade de vida."),
    "JU_D": ("ju", 63.28, 74.30, "Na Homa Institute, nós não tratamos apenas o peso: investigamos o que está por trás dele e construímos um tratamento integrativo e individualizado para você."),
    "JU_E": ("ju", 74.48, 77.00, "Você está esperando o que para começar?"),
}
# janela vertical do recorte por fonte (y inicial na fonte 720x1280)
YWIN = {"ju": 0, "vitorio": 130, "engordei": 0, "caixa": 380}

# b-roll: (fonte, entrada, saída, y)
B = {
    "carro": ("engordei", 13.0, 15.1, 0),
    "geladeira": ("engordei", 15.1, 17.0, 0),
    "burger": ("engordei", 11.0, 13.0, 0),
    "refri": ("engordei", 0.0, 3.9, 330),
    "clinica": ("engordei", 20.8, 23.0, 0),
    "entrega": ("engordei", 23.0, 25.0, 0),
    "caixa": ("caixa", 1.0, 6.5, 380),
    "barriga": ("ju", 8.3, 12.4, 0),
    "coracao": ("ju", 13.0, 16.4, 0),
    "joelho": ("ju", 18.2, 23.5, 0),
    "gordura": ("ju", 25.3, 31.5, 0),
    "pressao": ("ju", 33.2, 37.4, 0),
    "noite": ("ju", 38.4, 42.5, 0),
}
# cartelas finais do cliente (tela cheia, sem legenda por cima)
CARDS = {
    "preco": ("engordei", 26.0, 28.0),
    "whats": ("engordei", 28.8, 30.7),
}

# ---------------------------------------------------------------- roteiros
NAR = {
    "v1": [
        "Você fecha a boca, pula refeição... e a balança não sai do lugar? Então escuta isso.",
        "Não é preguiça. E não é falta de força de vontade. Depois dos 40, hormônio, inflamação e metabolismo mudam o jogo... e dieta sozinha não resolve.",
        "Protocolo de emagrecimento com acompanhamento médico, em português, aqui em Orlando. A partir de US$ 30,99 por semana. Toca no botão e chama a gente no WhatsApp.",
    ],
    "v2": [
        "Se você passou dos 40 e acha que emagrecer é vaidade... escuta isso.",
        "Cada quilo a mais pesa no coração, nas articulações, na pressão... e muitas vezes o problema começa bem antes de aparecer nos exames.",
        "Na Homa Institute, o seu protocolo começa com avaliação médica e tem acompanhamento do início ao fim, em português, aqui em Orlando. Chama a gente no WhatsApp e agenda a sua avaliação.",
    ],
    "v3": [
        "Brasileira que engordou depois que veio pros Estados Unidos: a culpa não é sua.",
        "Dois empregos, almoço no carro, porção americana... e a saudade que vira fome à noite. O corpo sente.",
        "E tentar resolver sozinha, com dieta da internet ou caneta comprada de conhecida, pode custar dinheiro, músculo e saúde.",
        "Na Homa Institute você faz o protocolo de emagrecimento com acompanhamento médico, em português, aqui em Orlando, a partir de US$ 30,99 por semana. Toca no botão e fala com a nossa equipe no WhatsApp.",
    ],
}
HOOK = {"v1": "A BALANÇA TRAVOU?", "v2": "EMAGRECER É VAIDADE?", "v3": "BRASILEIRA ENGORDA NOS EUA"}

# blocos: ("nar", indice, [shots]) | ("bite", chave[, [shots]]) | ("hold", segundos, [shots])
# shot: nome em B (painel) ou "card:<nome>" (tela cheia); "nome@palavra" faz o shot
# começar quando a narração diz aquela palavra
EDL = {
    "v1": [
        ("nar", 0, ["carro", "geladeira", "burger"]),
        ("bite", "VIT_A", ["barriga"]),  # áudio do Vitório sobre b-roll: esconde o título antigo da fonte
        ("bite", "VIT_B"),
        ("bite", "VIT_C"),
        ("nar", 1, ["gordura", "pressao", "noite"]),
        ("bite", "JU_D"),
        ("nar", 2, ["clinica", "entrega", "caixa", "card:preco@partir", "card:whats@Toca"]),
        ("hold", 0.8, ["card:whats"]),
    ],
    "v2": [
        ("nar", 0, ["barriga", "geladeira"]),
        ("bite", "JU_A"),
        ("nar", 1, ["coracao", "joelho", "pressao"]),
        ("bite", "JU_B"),
        ("bite", "JU_C"),
        ("nar", 2, ["clinica", "entrega", "caixa", "card:whats@Chama"]),
        ("bite", "JU_E"),
        ("hold", 2.0, ["card:whats"]),
    ],
    "v3": [
        ("nar", 0, ["refri"]),
        ("nar", 1, ["carro", "burger", "geladeira", "barriga"]),
        ("nar", 2, ["gordura", "pressao"]),
        ("bite", "VIT_D"),
        ("nar", 3, ["clinica", "entrega", "caixa", "card:preco@partir", "card:whats@Toca"]),
        ("hold", 0.8, ["card:whats"]),
    ],
}
MAX_STRETCH = 1.35  # b-roll curto pode ser desacelerado até 35% antes de congelar


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(" ".join(cmd) + "\n" + r.stderr[-3000:])
        raise SystemExit(1)
    return r.stdout


def dur(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]))


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9$]", "", w)


def align(text, heard):
    """Leva os tempos das palavras ouvidas (whisper) para as palavras do texto autoral."""
    toks = text.split()
    a = [norm(t) for t in toks]
    b = [norm(h[0]) for h in heard]
    times = [None] * len(toks)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = (heard[blk.b + k][1], heard[blk.b + k][2])
    t0 = heard[0][1] if heard else 0.0
    t1 = heard[-1][2] if heard else 1.0
    i = 0
    while i < len(toks):
        if times[i] is None:
            j = i
            while j < len(toks) and times[j] is None:
                j += 1
            s = times[i - 1][1] if i > 0 else t0
            e = times[j][0] if j < len(toks) else t1
            step = max(e - s, 0.05 * (j - i)) / (j - i)
            for k in range(i, j):
                times[k] = (s + step * (k - i), s + step * (k - i + 1))
            i = j
        else:
            i += 1
    return [(toks[k], times[k][0], times[k][1]) for k in range(len(toks))]


_whisper = None


def whisper_words(path):
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = _whisper.transcribe(path, language="pt", word_timestamps=True)
    return [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]


def make_panel_png(path):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(PANEL_H, H):
        t = (y - PANEL_H) / (H - PANEL_H)
        c = tuple(int(GREEN_TOP[i] + (GREEN_BOT[i] - GREEN_TOP[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    d.rectangle([0, PANEL_H, W, PANEL_H + 5], fill=GOLD)
    f1 = ImageFont.truetype(FONT, 30)
    brand = "H O M A   I N S T I T U T E   ·   O R L A N D O"
    bw = d.textlength(brand, font=f1)
    d.text(((W - bw) / 2, PANEL_H + 34), brand, font=f1, fill=GOLD)
    f2 = ImageFont.truetype(FONT, 24)
    foot = "Sujeito à avaliação médica e prescrição. Resultados variam."
    fw = d.textlength(foot, font=f2)
    d.text(((W - fw) / 2, PANEL_H + 360), foot, font=f2, fill=(170, 190, 180))
    img.save(path)


def render_shot(out, kind, src, t0, n_frames, y=0, stretch=1.0):
    srcf = f"src/{src}.mp4"
    pad = "tpad=stop_mode=clone:stop_duration=30"
    slow = f"setpts={stretch:.4f}*(PTS-STARTPTS)," if stretch > 1.001 else "setpts=PTS-STARTPTS,"
    if kind == "card":
        vf = f"[1:v]scale={W}:{H}:flags=lanczos,setsar=1,{slow}fps={FPS},{pad}[o]"
    else:
        vf = (f"[1:v]crop={CROP_W}:{CROP_H}:0:{y},scale={W}:{PANEL_H}:flags=lanczos,setsar=1,"
              f"{slow}fps={FPS},{pad}[f];[0:v][f]overlay=0:0[o]")
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", f"{WORK}/panel.png",
         "-ss", f"{t0:.3f}", "-i", srcf, "-filter_complex", vf, "-map", "[o]",
         "-frames:v", str(n_frames), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
         "-pix_fmt", "yuv420p", "-r", str(FPS), out])


def audio_clip(out, src, t0, t1, n_frames):
    d = n_frames / FPS
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", src,
         "-af", f"loudnorm=I=-15:LRA=9:TP=-1.5,afade=t=in:d=0.03,areverse,afade=t=in:d=0.04,areverse,"
                f"apad,atrim=0:{d:.4f},aresample=48000",
         "-ac", "2", "-ar", "48000", out])


def silence(out, n_frames):
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-t", f"{n_frames / FPS:.4f}", out])


def nar_chunks(vid):
    path = f"nar/{vid}.mp3"
    total = dur(path)
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "silencedetect=noise=-40dB:d=0.9",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    pairs = [(s, e) for s, e in zip(st, en) if s > 0.5 and e < total - 0.3]
    need = len(NAR[vid]) - 1
    pairs = sorted(sorted(pairs, key=lambda p: p[1] - p[0], reverse=True)[:need])
    assert len(pairs) == need, (vid, pairs)
    bounds = [0.0] + [x for s, e in pairs for x in (s + 0.22, e - 0.18)] + [total]
    return [(bounds[2 * i], bounds[2 * i + 1]) for i in range(need + 1)]


def chunk_caption_events(words, offset):
    """Agrupa palavras em blocos curtos e gera eventos com a palavra ativa em dourado."""
    chunks, cur, clen = [], [], 0
    for w in words:
        wl = len(w[0]) + 1
        if cur and (clen + wl > 24 or len(cur) >= 4):
            chunks.append(cur)
            cur, clen = [], 0
        cur.append(w)
        clen += wl
        if re.search(r"[.?!:]$", w[0]):
            chunks.append(cur)
            cur, clen = [], 0
    if cur:
        chunks.append(cur)
    ev = []
    for ci, ch in enumerate(chunks):
        end = ch[-1][2] + 0.2
        if ci + 1 < len(chunks) and chunks[ci + 1][0][1] - ch[-1][2] < 0.7:
            end = chunks[ci + 1][0][1]
        txt = [x[0].upper() for x in ch]
        line_break = None
        if sum(len(t) + 1 for t in txt) > 16 and len(txt) > 1:
            best, acc = None, 0
            for k in range(1, len(txt)):
                acc += len(txt[k - 1]) + 1
                diff = abs(acc - (sum(len(t) + 1 for t in txt) - acc))
                if best is None or diff < best[0]:
                    best = (diff, k)
            line_break = best[1]
        for wi, w in enumerate(ch):
            s = w[1] if wi > 0 else ch[0][1]
            e = ch[wi + 1][1] if wi + 1 < len(ch) else end
            parts = []
            for k, t in enumerate(txt):
                if k == line_break:
                    parts.append("\\N")
                elif k > 0:
                    parts.append(" ")
                parts.append("{\\c&H76B6D6&}" + t + "{\\c&HFFFFFF&}" if k == wi else t)
            ev.append((offset + s, offset + e, "".join(parts)))
    return ev


def ass_time(t):
    t = max(t, 0)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_ass(path, events, hook, hook_end):
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat ExtraBold,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,2,5,60,60,0,1
Style: Hook,Montserrat ExtraBold,70,&H00FFFFFF,&H00FFFFFF,&H00313D16,&H00313D16,0,0,0,0,100,100,1,0,3,22,0,8,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [hdr]
    if hook:
        lines.append(f"Dialogue: 1,{ass_time(0.05)},{ass_time(hook_end)},Hook,,0,0,0,,{{\\pos(540,140)\\fad(120,150)}}{hook}\n")
    for s, e, t in events:
        lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{{\\pos(540,1340)}}{t}\n")
    open(path, "w").write("".join(lines))


def build(vid, preview=False):
    os.makedirs(f"{WORK}/{vid}", exist_ok=True)
    wd = f"{WORK}/{vid}"
    words_db = json.load(open("words.json"))
    chunks = nar_chunks(vid)
    shot_files, audio_files, cap_events = [], [], []
    t = 0.0
    card_ranges = []
    first_block_end = None
    for bi, blk in enumerate(EDL[vid]):
        if blk[0] == "nar":
            a0, a1 = chunks[blk[1]]
            n = round((a1 - a0) * FPS)
            af = f"{wd}/a{bi:02d}.wav"
            audio_clip(af, f"nar/{vid}.mp3", a0, a1, n)
            heard = whisper_words(af)
            words = align(NAR[vid][blk[1]], heard)
            shots = blk[2]
        elif blk[0] == "bite":
            src, b0, b1, text = BITES[blk[1]]
            n = round((b1 - b0) * FPS)
            af = f"{wd}/a{bi:02d}.wav"
            audio_clip(af, f"src/{src}.mp4", b0, b1, n)
            heard = [(w, s - b0, e - b0) for w, s, e in words_db[f"src/{src}.mp4"] if s >= b0 - 0.05 and e <= b1 + 0.05]
            words = align(text, heard)
            shots = blk[2] if len(blk) > 2 else [("talk", src, b0, b1)]
        else:  # hold
            n = round(blk[1] * FPS)
            af = f"{wd}/a{bi:02d}.wav"
            silence(af, n)
            words = []
            shots = blk[2]
        audio_files.append(af)
        # monta os shots e os pontos de entrada ancorados em palavras da fala
        specs = []
        for sh in shots:
            anchor = None
            if isinstance(sh, tuple):
                _, src, s0, s1 = sh
                spec = ["panel", src, s0, s1, YWIN[src]]
            else:
                if "@" in sh:
                    sh, anchor = sh.split("@")
                if sh.startswith("card:"):
                    src, s0, s1 = CARDS[sh[5:]]
                    spec = ["card", src, s0, s1, 0]
                else:
                    src, s0, s1, y = B[sh]
                    spec = ["panel", src, s0, s1, y]
            start = None
            if anchor:
                hit = [w for w in words if norm(w[0]) == norm(anchor)]
                assert hit, (vid, anchor)
                start = round(max(hit[0][1] - 0.25, 0) * FPS)
            specs.append(spec + [start])
        # grupos entre âncoras: cada grupo preenche até a próxima âncora
        groups, cur = [], []
        for sp in specs:
            if sp[5] is not None and cur:
                groups.append(cur)
                cur = []
            cur.append(sp)
        groups.append(cur)
        starts = [g[0][5] if g[0][5] is not None else 0 for g in groups] + [n]
        starts[0] = 0
        tt = t
        si = 0
        for gi, g in enumerate(groups):
            need = starts[gi + 1] - starts[gi]
            nat = sum(round((sp[3] - sp[2]) * FPS) for sp in g)
            stretch = min(max(need / nat, 1.0), MAX_STRETCH) if nat else 1.0
            left = need
            for k, (kind, src, s0, s1, y, _) in enumerate(g):
                if left <= 0:
                    break
                avail = round((s1 - s0) * FPS * stretch)
                take = left if k == len(g) - 1 else min(avail, left)
                out = f"{wd}/s{bi:02d}_{si}.mp4"
                render_shot(out, kind, src, s0, take, y, stretch if kind == "panel" else 1.0)
                shot_files.append(out)
                if kind == "card":
                    card_ranges.append((tt, tt + take / FPS))
                tt += take / FPS
                left -= take
                si += 1
        cap_events += chunk_caption_events(words, t) if words else []
        t += n / FPS
        if first_block_end is None:
            first_block_end = t
    # legenda some sobre as cartelas de tela cheia
    clipped = []
    for s, e, txt in cap_events:
        for cs, ce in card_ranges:
            if s < ce and e > cs:
                if s < cs:
                    e = cs
                else:
                    s = e
        if e - s > 0.05:
            clipped.append((s, e, txt))
    write_ass(f"{wd}/caps.ass", clipped, HOOK[vid], min(first_block_end, 3.2))
    with open(f"{wd}/shots.txt", "w") as f:
        for sf in shot_files:
            f.write(f"file '{os.path.abspath(sf)}'\n")
    with open(f"{wd}/audio.txt", "w") as f:
        for a in audio_files:
            f.write(f"file '{os.path.abspath(a)}'\n")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{wd}/shots.txt", "-c", "copy", f"{wd}/video.mp4"])
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{wd}/audio.txt", "-c:a", "pcm_s16le", f"{wd}/audio.wav"])
    out = f"homa_{vid}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", f"{wd}/video.mp4", "-i", f"{wd}/audio.wav",
         "-vf", f"ass={wd}/caps.ass:fontsdir=/usr/share/fonts/truetype/higgsfield",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out])
    print(vid, "ok", f"{dur(out):.2f}s", "cards:", [(round(a, 2), round(b, 2)) for a, b in card_ranges])


if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    make_panel_png(f"{WORK}/panel.png")
    targets = ["v1", "v2", "v3"] if sys.argv[1] == "all" else [sys.argv[1]]
    for v in targets:
        build(v)

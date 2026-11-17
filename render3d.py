"""Render dos POVs em 3D "joguinho" (personagens redondinhos, low-poly), estilo serie de suspense.

Pipeline: voz (edge-tts) -> linha do tempo de planos de camera (cortes a cada ~2-3 s) -> motor
three.js em Chromium headless (pov3d/engine.html) renderiza cada quadro -> legenda palavra a
palavra + carta/UI + titulo (Pillow) -> ffmpeg -> mix com a trilha original.
Roda de graca no GitHub Actions (Chromium + SwiftShader, sem GPU).
"""
import base64
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config
import estilos
import musica
import musica_real
import render as R
import tts

W, H, FPS = config.W, config.H, config.FPS
MOTOR = config.BASE_DIR / "pov3d" / "engine.html"
FLAGS = ["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"]
CORTE_MIN = 1.6


def _linha_do_tempo(cenas, tempos_cena):
    """Cada cena vira N planos (um por camera listada), com duracao >= CORTE_MIN."""
    shots = []
    for c, (a, b) in zip(cenas, tempos_cena):
        cams = c["cams"]
        dur = b - a
        n = max(1, min(len(cams), int(dur / CORTE_MIN)))
        cams = cams[:n]
        for i, cam in enumerate(cams):
            shots.append({"t0": a + dur * i / n, "t1": a + dur * (i + 1) / n, "amb": c["amb"], "cam": cam,
                          "falante": c.get("falante", "")})
    shots[0]["t0"] = 0.0
    shots[-1]["t1"] = tempos_cena[-1][1] + 2.0
    return shots


# ---------------------------------------------------------------- overlays
def _fonte_carta(tam):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, tam)
    return ImageFont.load_default()


def _carta(linhas, mostrar_chars, titulo="Carta ao Rei D. Manuel"):
    """Pergaminho (a 'tela do celular' do Tiao): texto digitado aos poucos."""
    w, h = 820, 700
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([34, 40, w + 34, h + 40], radius=34, fill=(0, 0, 0, 120))          # sombra
    d.rounded_rectangle([20, 20, w + 20, h + 20], radius=34, fill=(238, 220, 176, 250), outline=(120, 80, 40, 255), width=8)
    ft, fc = _fonte_carta(44), _fonte_carta(42)
    d.text((60, 52), titulo, font=ft, fill=(110, 40, 30, 255))
    d.line([(60, 120), (w - 20, 120)], fill=(120, 80, 40, 255), width=4)
    y, restante = 150, mostrar_chars
    for ln in linhas:
        if restante <= 0:
            break
        parte = ln[:restante]
        restante -= len(ln)
        d.text((60, y), parte, font=fc, fill=(50, 30, 20, 255))
        y += 62
    return im


def _barra_ep(ep, titulo):
    f1, f2 = R._fonte(60), R._fonte(46)
    w = 900
    im = Image.new("RGBA", (w, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, 90], radius=36, fill=(255, 214, 10, 250), outline=(10, 8, 20, 255), width=6)
    bb = f1.getbbox(ep)
    d.text(((w - (bb[2] - bb[0])) // 2 - bb[0], 12 - bb[1] + 4), ep, font=f1, fill=(15, 10, 30, 255))
    t = R._texto_contorno(titulo.upper(), 70, (255, 255, 255), 8)
    if t.width > w:
        k = w / t.width
        t = t.resize((int(t.width * k), int(t.height * k)), Image.LANCZOS)
    im.alpha_composite(t, ((w - t.width) // 2, 100))
    return im


# ---------------------------------------------------------------- render
def render_pov3d(conteudo: dict, out_path: Path, estilo_nome: str | None = None, fake_tts: bool = False,
                 largura: int | None = None):
    from playwright.sync_api import sync_playwright
    import os
    work = config.OUT_DIR / f"_work_{conteudo['id']}"
    work.mkdir(parents=True, exist_ok=True)
    estilo = estilos.ESTILOS[estilo_nome or conteudo.get("estilo") or "sepia"]
    cenas = conteudo["cenas"]

    sintetizar = tts.synthesize_sentences
    if fake_tts or os.environ.get("PLANOB_FAKE_TTS") == "1":
        import tts_fake
        sintetizar = tts_fake.synthesize_sentences
    segs_por_cena = [sintetizar(c["fala"], work / f"voz{i:02d}") for i, c in enumerate(cenas)]
    todos = [s for ss in segs_por_cena for s in ss]
    inicios, env, dur_voz = R._montar_audio(todos, work / "voz.wav")
    tempos_cena, k = [], 0
    for ss in segs_por_cena:
        a = inicios[k]
        k += len(ss)
        b = inicios[k] if k < len(inicios) else dur_voz
        tempos_cena.append((a, b))
    palavras = R._palavras_abs(todos, inicios)
    blocos = R._blocos_legenda(palavras)
    total = dur_voz + 1.6
    nframes = int(total * FPS)
    shots = _linha_do_tempo(cenas, tempos_cena)

    segmentos = musica_real.plano_por_cenas(cenas, tempos_cena, estilo.musica)
    music_wav = work / "musica.wav"
    faixas = musica_real.gerar(total + 1, segmentos, str(music_wav), seed=R.hash_seed(conteudo["id"], 9, 9))
    if faixas is None:
        musica.gerar(total + 2, estilo.musica, str(music_wav), seed=R.hash_seed(conteudo["id"], 9, 9))

    video_tmp = work / "video.mp4"
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", str(video_tmp)], stdin=subprocess.PIPE)

    vig = R._vinheta(0.55)
    palavra_inicios = np.array([p[1] for p in palavras])
    ep = conteudo.get("episodio", "EPI. 01")
    barra = _barra_ep(ep, conteudo.get("titulo_curto") or conteudo["titulo"])
    uis = [(tempos_cena[i], c["ui"]) for i, c in enumerate(cenas) if c.get("ui")]
    bloco_idx = 0

    with sync_playwright() as pw:
        br = pw.chromium.launch(args=FLAGS)
        pg = br.new_page(viewport={"width": W, "height": H})
        pg.goto(MOTOR.resolve().as_uri())
        pg.wait_for_timeout(600)
        pg.evaluate("s => window.setShots(s)", shots)
        for fi in range(nframes):
            t = fi / FPS
            amp = float(env[min(fi, len(env) - 1)]) if fi < len(env) else 0.0
            dados = pg.evaluate("([t, a]) => window.frame(t, a)", [t, amp])
            buf = np.frombuffer(base64.b64decode(dados.split(",", 1)[1]), np.uint8)
            frame = cv2.cvtColor(cv2.imdecode(buf, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
            if frame.shape[1] != W:
                frame = cv2.resize(frame, (W, H))
            frame = cv2.multiply(frame, vig, scale=1 / 255.0)

            # soco de zoom/flash no corte (energia, como nos videos de referencia)
            for s in shots:
                if s["t0"] <= t < s["t0"] + 0.12 and s["t0"] > 0.1:
                    fl = 0.18 * (1 - (t - s["t0"]) / 0.12)
                    frame = cv2.addWeighted(frame, 1 - fl, np.full_like(frame, 255), fl, 0)
                    break

            # carta (UI dentro da cena)
            for (a, b), ui in uis:
                if a - 0.1 <= t <= b + 0.5:
                    linhas = ui["linhas"]
                    total_ch = sum(len(x) for x in linhas)
                    prog = min(1.0, max(0.0, (t - a) / max(0.5, (b - a) * 0.7)))
                    im = _carta(linhas, int(total_ch * prog), ui.get("titulo", "Carta ao Rei D. Manuel"))
                    ent = min(1.0, (t - a + 0.1) / 0.25)
                    _off = int((1 - ent) * 140)
                    R._blit(frame, im, (W - im.width) // 2, int(H * 0.30) + _off, opac=min(1.0, ent))
                    break

            # chip do episodio + titulo (primeiros 3 s)
            if t < 3.2:
                ent = min(1.0, t / 0.3)
                sai = min(1.0, (3.2 - t) / 0.35)
                R._blit(frame, barra, (W - barra.width) // 2, int(H * 0.06) + int((1 - ent) * -90), opac=min(ent, sai))

            # legenda palavra a palavra (destaque amarelo/laranja)
            while bloco_idx < len(blocos) - 1 and t >= blocos[bloco_idx][-1][2] + 0.05 and t >= blocos[bloco_idx + 1][0][1] - 0.02:
                bloco_idx += 1
            bl = blocos[bloco_idx]
            if bl[0][1] - 0.05 <= t <= bl[-1][2] + 0.35:
                ativa = 0
                for j, w in enumerate(bl):
                    if t >= w[1] - 0.02:
                        ativa = j
                spr = R._chunk_sprite(tuple(x[0] for x in bl), ativa, (255, 214, 10), None, 96)
                pop = 1.0 + 0.12 * max(0.0, 1 - (t - bl[ativa][1]) / 0.12)
                im = spr if pop < 1.01 else spr.resize((int(spr.width * pop), int(spr.height * pop)), Image.BILINEAR)
                R._blit(frame, im, (W - im.width) // 2, int(H * (0.235 if t < 3.2 else 0.17)) - im.height // 2)

            cv2.rectangle(frame, (0, 0), (int(W * fi / nframes), 10), (255, 214, 10), -1)
            if t > 3.2:
                h_im = R._texto_contorno(R.HANDLE, 40, (255, 255, 255), 6)
                R._blit(frame, h_im, W - h_im.width - 20, 36, opac=0.8)
            proc.stdin.write(frame.tobytes())
            if fi % 150 == 0:
                print(f"[render3d] quadro {fi}/{nframes}", flush=True)
        br.close()
    proc.stdin.close()
    proc.wait()

    vol_m = 1.0 if faixas else 0.22
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_tmp), "-i", str(work / "voz.wav"), "-i", str(music_wav),
         "-filter_complex",
         f"[1:a]volume=1.35,aresample=44100,aformat=channel_layouts=stereo,apad,asplit=2[v1][v2];"
         f"[2:a]aresample=44100,aformat=channel_layouts=stereo,volume={vol_m}[m];"
         f"[m][v1]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=300[md];"
         f"[v2][md]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", str(out_path)],
        check=True)
    return {"duracao": total, "estilo": estilo.nome}

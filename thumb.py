"""Thumbnail chamativa 1280x720 (alto contraste, texto gigante, Tic reagindo, cor do estilo)."""
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config
import estilos
import imagens
import mascote

TW, TH = 1280, 720
FONTE = config.ASSETS_DIR / "fontes" / "Anton-Regular.ttf"
PALAVRAS_FRACAS = {"de", "da", "do", "das", "dos", "o", "a", "os", "as", "um", "uma", "em", "no", "na", "que", "e", "se",
                   "tivesse", "sido", "para", "por", "com", "ao", "ou"}

CORES = {  # (texto forte, texto 2, faixa)
    "epico": ((255, 214, 10), (255, 255, 255), (214, 40, 40)),
    "sepia": ((255, 200, 60), (255, 255, 255), (190, 60, 30)),
    "neon": ((60, 255, 240), (255, 255, 255), (255, 40, 160)),
    "noir": ((255, 255, 255), (255, 214, 10), (200, 30, 30)),
    "aquarela": ((255, 230, 60), (255, 255, 255), (230, 70, 90)),
}


def _fonte(tam):
    return ImageFont.truetype(str(FONTE), tam)


def texto_gancho(c: dict) -> str:
    """Frase curta (2-4 palavras) para a thumbnail. Usa c['thumb_texto'] se existir."""
    if c.get("thumb_texto"):
        return c["thumb_texto"].upper()
    t = re.sub(r"^(POV:|Você acorda em|Você é|E se|Quem venceria:)\s*", "", c["titulo"], flags=re.I).rstrip("?!. ")
    fortes = [w for w in t.split() if w.lower() not in PALAVRAS_FRACAS]
    return " ".join(fortes[:4]).upper() + ("?" if c.get("formato") == "e-se" else "")


def _linhas(texto: str, max_chars=11):
    palavras, linhas, atual = texto.split(), [], ""
    for w in palavras:
        if atual and len(atual) + 1 + len(w) > max_chars:
            linhas.append(atual)
            atual = w
        else:
            atual = (atual + " " + w).strip()
    if atual:
        linhas.append(atual)
    return linhas[:3]


def _imagem_base(c: dict, estilo, idx_cena: int):
    from render import hash_seed
    cena = c["cenas"][idx_cena]
    rgb, _dep, _o = imagens.obter(cena["visuais"][0], estilo, seed=hash_seed(c["id"], idx_cena, 0))
    h, w = rgb.shape[:2]
    alvo_h = int(w * TH / TW)
    y0 = int(max(0, min(h - alvo_h, h * 0.18)))
    faixa = rgb[y0:y0 + alvo_h]
    g = cv2.resize(faixa, (TW, TH), interpolation=cv2.INTER_CUBIC)
    # sat + contraste + nitidez
    hsv = cv2.cvtColor(g, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.35, 0, 255)
    g = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    g = cv2.convertScaleAbs(g, alpha=1.18, beta=-14)
    blur = cv2.GaussianBlur(g, (0, 0), 3)
    return cv2.addWeighted(g, 1.6, blur, -0.6, 0)


def gerar(c: dict, estilo_nome: str, saida: Path) -> Path:
    estilo = estilos.ESTILOS[estilo_nome]
    cor1, cor2, cor_faixa = CORES.get(estilo_nome, CORES["epico"])
    # cena mais forte: a que tem 'surpreso' no meio do roteiro, senao a 2a
    cand = [i for i, x in enumerate(c["cenas"]) if x.get("emocao") == "surpreso" and i > 0] or [min(1, len(c["cenas"]) - 1)]
    base = _imagem_base(c, estilo, cand[0])

    # escurece a esquerda para o texto estourar
    grad = np.linspace(0.30, 1.0, TW, dtype=np.float32)[None, :, None]
    base = (base.astype(np.float32) * grad).astype(np.uint8)
    vig = np.zeros((TH, TW), np.float32)
    cv2.ellipse(vig, (TW // 2, TH // 2), (int(TW * 0.75), int(TH * 0.85)), 0, 0, 360, 1, -1)
    vig = cv2.GaussianBlur(vig, (0, 0), 120)
    base = (base.astype(np.float32) * (0.55 + 0.45 * vig[..., None])).astype(np.uint8)
    im = Image.fromarray(base).convert("RGBA")
    d = ImageDraw.Draw(im)

    # faixa de formato (canto superior esquerdo)
    rotulo = {"e-se": "E SE...?", "voce-acorda": "VOCÊ ACORDA EM...", "quem-venceria": "QUEM VENCERIA?", "pov": "POV"}.get(
        c.get("formato", ""), "PLANO B")
    f_r = _fonte(64)
    bb = d.textbbox((0, 0), rotulo, font=f_r)
    d.rounded_rectangle([34, 30, 34 + (bb[2] - bb[0]) + 56, 30 + 96], 18, fill=cor_faixa + (255,), outline=(255, 255, 255, 255), width=5)
    d.text((34 + 28 - bb[0], 30 + 48 - (bb[3] - bb[1]) // 2 - bb[1]), rotulo, font=f_r, fill=(255, 255, 255, 255))

    # texto gancho gigante
    linhas = _linhas(texto_gancho(c))
    tam = 210 if len(linhas) == 1 else 190 if len(linhas) == 2 else 150
    f = _fonte(tam)
    y = 170 if len(linhas) < 3 else 150
    camada = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    dc = ImageDraw.Draw(camada)
    for i, ln in enumerate(linhas):
        cor = cor1 if i % 2 == 0 else cor2
        wln = dc.textlength(ln, font=f)
        x = 40
        if wln > 820:
            f2 = _fonte(int(tam * 820 / wln))
        else:
            f2 = f
        dc.text((x + 8, y + 10), ln, font=f2, fill=(0, 0, 0, 200), stroke_width=14, stroke_fill=(0, 0, 0, 200))
        dc.text((x, y), ln, font=f2, fill=cor + (255,), stroke_width=12, stroke_fill=(8, 6, 16, 255))
        y += int(f2.size * 0.98)
    camada = camada.rotate(3, resample=Image.BICUBIC, center=(0, TH))
    im.alpha_composite(camada)

    # Tic grande, espantado, a direita
    spr = mascote.sprite(1.3, 0.6, True, "surpreso", altura=560)
    im.alpha_composite(spr, (TW - spr.width - 20, TH - spr.height - 6))

    # contorno externo claro para destacar no feed
    d2 = ImageDraw.Draw(im)
    d2.rectangle([0, 0, TW - 1, TH - 1], outline=cor1 + (255,), width=10)
    saida.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(saida, quality=92)
    return saida

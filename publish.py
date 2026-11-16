#!/usr/bin/env python3
"""Renderiza e publica o(s) proximo(s) video(s) do Plano B da Historia.

Uso:
  python publish.py                 # publica 1 video pendente (o mais antigo)
  python publish.py --max 2         # ate 2
  python publish.py --id 03-einstein-newton
  python publish.py --dry-run       # renderiza e NAO envia (teste)
O que ja foi publicado fica em state/publicados.json; o que foi medido em state/videos.json.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import config
import estilos
import render

PUB = config.STATE_DIR / "publicados.json"
VIDEOS = config.STATE_DIR / "videos.json"
HASHTAGS = "#shorts #historia #historiaalternativa #eseo #curiosidades #brasil"


class CotaEsgotada(Exception):
    pass


def _ler(p, padrao):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return padrao


def pendentes() -> list:
    feitos = {d["id"] for d in _ler(PUB, [])}
    itens = []
    for arq in sorted(config.CONTEUDO_DIR.glob("*.json")):
        try:
            c = json.loads(arq.read_text(encoding="utf-8"))
        except Exception:
            continue
        if c.get("id") and c["id"] not in feitos and not c["id"].startswith("00-"):
            itens.append(c)
    itens.sort(key=lambda c: (c.get("ordem", 999), c["id"]))
    return itens


def _descricao(c: dict) -> str:
    return (f"{c['descricao']}\n\nSe inscreva no Plano B da História: toda semana, um \"e se...\" que muda o mundo.\n"
            f"Comente qual história alternativa você quer ver no próximo vídeo!\n\n"
            f"Conteúdo especulativo e educativo: os fatos citados são históricos, as hipóteses são imaginação.\n\n{HASHTAGS}")


def _enviar_youtube(video: Path, c: dict) -> str:
    import upload
    from googleapiclient.errors import HttpError
    try:
        return upload.upload_video(video, c["titulo"][:92] + " #shorts" if len(c["titulo"]) <= 92 else c["titulo"][:100],
                                   _descricao(c), c.get("tags", []) + ["shorts"], None, True)
    except HttpError as exc:
        if "quota" in str(exc).lower() or "uploadLimitExceeded" in str(exc):
            raise CotaEsgotada(str(exc)[:200]) from exc
        raise


def registrar(c: dict, video_id: str, estilo: str, agora_iso: str, ig_id=None):
    pubs = [d for d in _ler(PUB, []) if d["id"] != c["id"]]
    pubs.append({"id": c["id"], "video_id": video_id, "publicado_em": agora_iso, "instagram": ig_id})
    PUB.write_text(json.dumps(pubs, ensure_ascii=False, indent=1), encoding="utf-8")
    vids = [d for d in _ler(VIDEOS, []) if d.get("video_id") != video_id]
    vids.append({"video_id": video_id, "item_id": c["id"], "titulo": c["titulo"], "estilo": estilo,
                 "formato": c.get("formato", ""), "publicado_em": agora_iso})
    VIDEOS.write_text(json.dumps(vids, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    ap.add_argument("--max", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    fila = pendentes()
    if a.id:
        todos = {json.loads(p.read_text(encoding="utf-8"))["id"]: json.loads(p.read_text(encoding="utf-8"))
                 for p in config.CONTEUDO_DIR.glob("*.json")}
        fila = [todos[a.id]] if a.id in todos else []
    if not fila:
        print("[publish] nada pendente - gere mais roteiros (roteirista.py).")
        return 0

    vids = _ler(VIDEOS, [])
    ultimo_estilo = vids[-1]["estilo"] if vids else None
    erros = 0
    for c in fila[: a.max]:
        estilo = c.get("estilo") or estilos.sortear(c["id"], evitar=ultimo_estilo)
        saida = config.OUT_DIR / f"{c['id']}.mp4"
        print(f"[publish] {c['id']} | estilo={estilo}", flush=True)
        try:
            render.render_video(c, saida, estilo)
        except Exception as exc:
            print(f"[publish] render falhou: {exc!r}")
            erros += 1
            continue
        ultimo_estilo = estilo
        if a.dry_run:
            print(f"[publish] dry-run: {saida}")
            continue
        try:
            vid = _enviar_youtube(saida, c)
        except CotaEsgotada as exc:
            print(f"[publish] cota diaria do YouTube esgotada: {exc}")
            return 2
        except Exception as exc:
            print(f"[publish] upload falhou: {exc!r}")
            erros += 1
            continue
        print(f"[publish] YouTube OK: https://youtube.com/shorts/{vid}", flush=True)
        import instagram
        legenda = f"{c['titulo']}\n\nSegue @planobdahistoria pra mais histórias alternativas! Comenta qual quer ver.\n\n#historia #historiaalternativa #eseo #curiosidades #brasil"
        ig = instagram.postar(saida, legenda)
        registrar(c, vid, estilo, datetime.now(timezone.utc).isoformat(timespec="seconds"), ig)
    return 1 if erros and not a.dry_run and erros == len(fila[: a.max]) else 0


if __name__ == "__main__":
    sys.exit(main())

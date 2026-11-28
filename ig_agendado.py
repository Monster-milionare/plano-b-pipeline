#!/usr/bin/env python3
"""Instagram dos videos AGENDADOS: a API do Instagram nao agenda, entao este script (de hora em hora) acha o video
agendado que acabou de ir ao ar no YouTube e ainda nao foi pro Instagram. Escreve id=<roteiro> em $GITHUB_OUTPUT."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import config


# O cron do GitHub pula muito: com janela de 4 h varios videos ficavam sem Reel.
JANELA_H = 10


def pendente():
    try:
        pubs = json.loads((config.STATE_DIR / "publicados.json").read_text(encoding="utf-8"))
    except Exception:
        return ""
    agora = datetime.now(timezone.utc)
    fila = []
    for d in sorted(pubs, key=lambda x: x.get("publicado_em", "")):
        if not d.get("agendado") or d.get("instagram"):
            continue
        try:
            t = datetime.fromisoformat(d["publicado_em"])
        except Exception:
            continue
        if t - timedelta(minutes=20) <= agora <= t + timedelta(hours=JANELA_H):
            try:
                c = json.loads((config.CONTEUDO_DIR / f"{d['id']}.json").read_text(encoding="utf-8"))
                if c.get("formato") == "longo":
                    continue
            except Exception:
                pass
            fila.append(d["id"])
    if not fila:
        return ""
    # alterna entre os pendentes: um video que falha no envio nao trava os outros
    return fila[int(os.environ.get("GITHUB_RUN_NUMBER") or 0) % len(fila)]


if __name__ == "__main__":
    i = pendente()
    print(f"[ig_agendado] {i or 'nada pra postar agora'}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"id={i}\n")
    sys.exit(0)

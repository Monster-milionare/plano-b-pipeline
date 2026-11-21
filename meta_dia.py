#!/usr/bin/env python3
"""Decide (so com a stdlib, rapido) se este disparo do agendador deve publicar um Short.

Meta: 4 Shorts por dia (horario de Brasilia). Janelas: 09h, 12h, 15h e 18h. Se o GitHub atrasar ou pular um
disparo, o disparo seguinte (de hora em hora) compensa, respeitando um intervalo minimo entre videos.
Escreve publicar=true|false em $GITHUB_OUTPUT.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
BRT = timezone(timedelta(hours=-3))
META = int(os.environ.get("META_SHORTS", "4"))
JANELAS = [9, 12, 15, 18][:META] if META <= 4 else [9, 11, 13, 15, 17, 19][:META]
INTERVALO_MIN = 70  # minutos entre dois videos


def _ler(p, padrao):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return padrao


def eh_short(vid_id: str) -> bool:
    c = _ler(BASE / "conteudo" / f"{vid_id}.json", {})
    return c.get("formato") != "longo"


def decidir(agora=None):
    agora = (agora or datetime.now(timezone.utc)).astimezone(BRT)
    pubs = _ler(BASE / "state" / "publicados.json", [])
    hoje, ultimo = 0, None
    for d in pubs:
        try:
            t = datetime.fromisoformat(d["publicado_em"]).astimezone(BRT)
        except Exception:
            continue
        if not eh_short(d["id"]):
            continue
        if ultimo is None or t > ultimo:
            ultimo = t
        if t.date() == agora.date():
            hoje += 1
    esperado = sum(1 for h in JANELAS if agora.hour >= h)
    if hoje >= META:
        return False, f"meta do dia batida ({hoje}/{META})"
    if hoje >= esperado:
        return False, f"em dia: {hoje} publicados, {esperado} esperados ate as {agora:%H}h"
    if ultimo and (agora - ultimo) < timedelta(minutes=INTERVALO_MIN):
        return False, f"ultimo Short foi ha {int((agora - ultimo).total_seconds() // 60)} min (minimo {INTERVALO_MIN})"
    return True, f"atrasado: {hoje} publicados, {esperado} esperados ate as {agora:%H}h"


if __name__ == "__main__":
    ok, motivo = decidir()
    print(f"[meta_dia] publicar={ok} ({motivo})")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"publicar={'true' if ok else 'false'}\n")
    sys.exit(0)

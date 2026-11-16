#!/usr/bin/env python3
"""Escreve roteiros novos no mesmo formato dos 10 de teste, via Groq (gratis).
Pega o proximo tema de temas.txt que ainda nao virou conteudo/*.json.
Valida (tamanho, estrutura, sem tracos longos) e tenta ate 3 vezes."""
import json
import re
import sys
import unicodedata

import requests

import config

PROMPT = """Voce escreve roteiros de YouTube Shorts em portugues do Brasil para o canal "Plano B da Historia" (historia alternativa).
Formato do video: {formato}. Tema: {titulo}

Regras OBRIGATORIAS:
- Entre 85 e 125 palavras de narracao no total, frases curtas (4 a 16 palavras), tom empolgado e direto, falando com "voce".
- Cena 1 e um gancho forte que repete a pergunta do titulo; a ultima cena pede um comentario.
- FATOS historicos citados (datas, nomes, numeros) devem ser REAIS e verificaveis; a parte hipotetica deve vir marcada com "talvez", "imagine", "e so uma hipotese". Se nao tiver certeza de um fato, NAO cite.
- Escreva numeros por extenso quando forem falados (ex: "mil quatrocentos e noventa e quatro"), mas o campo "ano" pode ter digitos.
- Nada de tracos longos, emojis ou asteriscos.
- 6 a 8 cenas. Cada cena: "fala" (1 a 2 frases), "visuais" (lista com 1 ou 2 descricoes em INGLES, concretas, de uma imagem vertical, sem texto escrito na imagem), "emocao" (neutro|feliz|surpreso|preocupado), opcional "ano" (curto, ex "1500", "22 ABR"), "destaques" (1 a 3 palavras da fala que merecem enfase).
- Se o formato for "pov": narre em PRIMEIRA PESSOA, como se o espectador fosse o personagem do titulo ("Eu sou ...", "Eu sinto ..."). Cada descricao em "visuais" deve comecar com "first person view" (camera na visao do personagem, maos ou objetos do personagem em primeiro plano). Termine perguntando o que o espectador faria no lugar do personagem.
Responda SOMENTE com JSON valido: {{"descricao": "...", "tags": ["..."], "cenas": [ ... ]}}"""


def _slug(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40]


def proximo_tema():
    feitos = {p.stem.split("-", 1)[1] for p in config.CONTEUDO_DIR.glob("*.json") if "-" in p.stem}
    for linha in (config.BASE_DIR / "temas.txt").read_text(encoding="utf-8").splitlines():
        if "|" not in linha:
            continue
        fmt, titulo = linha.split("|", 1)
        if _slug(titulo) not in feitos:
            return fmt.strip(), titulo.strip()
    return None


def _validar(d: dict):
    cenas = d.get("cenas")
    if not isinstance(cenas, list) or not 5 <= len(cenas) <= 9:
        return "numero de cenas fora de 5-9"
    total = 0
    for c in cenas:
        if not isinstance(c.get("fala"), str) or not isinstance(c.get("visuais"), list) or not c["visuais"]:
            return "cena sem fala/visuais"
        if any(x in c["fala"] for x in ("—", "–", "*", "#")):
            return "caractere proibido na fala"
        total += len(c["fala"].split())
        c.setdefault("emocao", "neutro")
        if c["emocao"] not in ("neutro", "feliz", "surpreso", "preocupado"):
            c["emocao"] = "neutro"
    if not 80 <= total <= 135:
        return f"{total} palavras (precisa 80-135)"
    return None


def gerar(fmt: str, titulo: str):
    if not config.GROQ_API_KEY:
        print("[roteirista] GROQ_API_KEY ausente.")
        return None
    for tentativa in range(3):
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", timeout=120,
                              headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
                              json={"model": config.GROQ_MODEL, "temperature": 0.8,
                                    "response_format": {"type": "json_object"},
                                    "messages": [{"role": "user", "content": PROMPT.format(formato=fmt, titulo=titulo)}]})
            d = json.loads(r.json()["choices"][0]["message"]["content"])
            erro = _validar(d)
            if erro:
                print(f"[roteirista] tentativa {tentativa + 1}: {erro}")
                continue
            return d
        except Exception as exc:
            print(f"[roteirista] tentativa {tentativa + 1} falhou: {str(exc)[:120]}")
    return None


def main() -> int:
    if "--se-fila-curta" in sys.argv:
        import publish
        if len(publish.pendentes()) >= 3:
            print("[roteirista] fila com 3+ roteiros - nada a escrever.")
            return 0
    t = proximo_tema()
    if not t:
        print("[roteirista] temas.txt acabou - adicione mais temas.")
        return 0
    fmt, titulo = t
    d = gerar(fmt, titulo)
    if not d:
        return 0
    ordem = 1 + max([json.loads(p.read_text(encoding="utf-8")).get("ordem", 0) for p in config.CONTEUDO_DIR.glob("*.json")] or [0])
    c = {"id": f"{ordem:02d}-{_slug(titulo)}", "ordem": ordem, "formato": fmt, "titulo": titulo,
         "descricao": d.get("descricao", titulo), "tags": d.get("tags", []), "cenas": d["cenas"]}
    (config.CONTEUDO_DIR / f"{c['id']}.json").write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[roteirista] novo roteiro: {c['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

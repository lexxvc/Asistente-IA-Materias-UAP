"""
Script de evaluación del Asistente UAP.

Corre las preguntas de prueba contra el MISMO prompt y contexto de producción
(base_conocimiento.py), aplica verificaciones automáticas y genera un reporte
para revisión manual antes de publicar cualquier cambio de prompt, modelo o base.

Uso:
    export GEMINI_API_KEY="tu_key"
    python evaluacion/eval_preguntas.py            # todas las preguntas
    python evaluacion/eval_preguntas.py 3 10 21    # solo algunas (por id)

Genera: evaluacion/resultados_YYYY-MM-DD_HHMM.md

Campos opcionales por pregunta en preguntas_prueba.json:
    maestria             → simula la maestría elegida en el selector
    historial            → lista de turnos previos [{"rol": "user"|"model", "texto": "..."}]
    debe_contener        → TODOS estos textos deben aparecer (sin importar mayúsculas/acentos)
    debe_contener_alguno → AL MENOS uno debe aparecer
    no_debe_contener     → NINGUNO debe aparecer
"""

import datetime
import json
import os
import sys
import time
import unicodedata

from google import genai
from google.genai import types

RUTA_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RUTA_BASE)
import base_conocimiento as bc  # noqa: E402

MODELO = "gemini-2.5-flash"


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def verificar(respuesta: str, p: dict) -> list:
    """Devuelve la lista de fallos automáticos (vacía = pasa)."""
    r = normalizar(respuesta)
    fallos = []
    for t in p.get("debe_contener", []):
        if normalizar(t) not in r:
            fallos.append(f"falta «{t}»")
    alguno = p.get("debe_contener_alguno", [])
    if alguno and not any(normalizar(t) in r for t in alguno):
        fallos.append(f"no menciona ninguno de {alguno}")
    for t in p.get("no_debe_contener", []):
        if normalizar(t) in r:
            fallos.append(f"contiene «{t}»")
    return fallos


def tiene_checks(p: dict) -> bool:
    return any(k in p for k in ("debe_contener", "debe_contener_alguno", "no_debe_contener"))


def main():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: define la variable de entorno GEMINI_API_KEY")
        return
    cliente = genai.Client(api_key=api_key)

    print("Cargando base de conocimiento...")
    config = types.GenerateContentConfig(system_instruction=bc.system_prompt_completo())
    tokens = {"entrada": 0, "salida": 0, "razonamiento": 0}

    with open(os.path.join(RUTA_BASE, "evaluacion", "preguntas_prueba.json"), encoding="utf-8") as f:
        preguntas = json.load(f)["preguntas"]
    ids = {int(a) for a in sys.argv[1:] if a.isdigit()}
    if ids:
        preguntas = [p for p in preguntas if p["id"] in ids]

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    salida = os.path.join(RUTA_BASE, "evaluacion", f"resultados_{timestamp}.md")
    cuerpo, resumen = [], []
    n_pasa = n_falla = n_manual = 0

    for p in preguntas:
        print(f"[{p['id']}] {p['pregunta'][:60]}...")
        historial = [types.Content(role=h["rol"], parts=[types.Part(text=h["texto"])])
                     for h in p.get("historial", [])]
        mensaje = bc.contexto_mensaje(p["pregunta"], p.get("maestria", ""))
        try:
            r = cliente.chats.create(model=MODELO, config=config, history=historial).send_message(mensaje)
            resp = r.text or ""
            u = r.usage_metadata
            if u:
                tokens["entrada"] += u.prompt_token_count or 0
                tokens["salida"] += u.candidates_token_count or 0
                tokens["razonamiento"] += u.thoughts_token_count or 0
        except Exception as e:
            resp = f"ERROR: {e}"
        time.sleep(1)  # respetar rate limits

        if not tiene_checks(p):
            estado = "👁️ revisión manual"
            n_manual += 1
            fallos = []
        else:
            fallos = verificar(resp, p)
            estado = "❌ FALLA" if fallos else "✅ pasa"
            n_falla += bool(fallos)
            n_pasa += not fallos
        resumen.append(f"| {p['id']} | {p['categoria']} | {estado} | {'; '.join(fallos)} |")

        cuerpo.append(f"## {p['id']}. [{p['categoria']}] — {estado}\n")
        if p.get("maestria"):
            cuerpo.append(f"**Maestría simulada:** {p['maestria']}\n")
        if p.get("historial"):
            cuerpo.append("**Historial previo:** " + " → ".join(h["texto"][:80] for h in p["historial"]) + "\n")
        cuerpo.append(f"**Pregunta:** {p['pregunta']}\n")
        cuerpo.append(f"**Se espera:** {p['espera']}\n")
        if fallos:
            cuerpo.append(f"**Fallos automáticos:** {'; '.join(fallos)}\n")
        cuerpo.append("**Respuesta obtenida:**\n\n> " + resp.replace("\n", "\n> ") + "\n")
        cuerpo.append("**Veredicto manual:** [ ] ✅  [ ] ⚠️  [ ] ❌\n\n---\n")

    encabezado = [
        f"# Resultados de evaluación — {timestamp}\n",
        f"Modelo: `{MODELO}` · Preguntas: {len(preguntas)} · "
        f"✅ {n_pasa} · ❌ {n_falla} · 👁️ manual {n_manual}\n",
        f"Tokens: entrada {tokens['entrada']:,} · salida {tokens['salida']:,} · "
        f"razonamiento {tokens['razonamiento']:,}\n",
        "Las verificaciones automáticas solo revisan palabras clave: revisa también cada respuesta.\n",
        "| # | Categoría | Automático | Detalle |", "|---|---|---|---|", *resumen, "\n---\n",
    ]
    with open(salida, "w", encoding="utf-8") as f:
        f.write("\n".join(encabezado + cuerpo))

    print(f"\n✅ {n_pasa} · ❌ {n_falla} · 👁️ {n_manual}  →  {salida}")
    sys.exit(1 if n_falla else 0)


if __name__ == "__main__":
    main()

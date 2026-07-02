"""
Script de evaluación del Asistente UAP.
Corre las 25 preguntas de prueba contra el pipeline real y genera un reporte
para revisión manual antes de publicar cualquier cambio de prompt o modelo.

Uso:
    export GEMINI_API_KEY="tu_key"
    python evaluacion/eval_preguntas.py

Genera: evaluacion/resultados_YYYY-MM-DD_HHMM.md
"""

import google.generativeai as genai
import os
import glob
import json
import datetime
import time

MODELO = "models/gemini-2.5-flash"
RUTA_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cargar_carpeta(ruta):
    archivos = glob.glob(f"{ruta}/**/*.md", recursive=True)
    archivos = sorted([a for a in archivos if "README" not in a])
    bloques = []
    for archivo in archivos:
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                contenido = f.read().strip()
            if contenido:
                bloques.append(contenido)
        except Exception:
            pass
    return "\n\n---\n\n".join(bloques)


def construir_base():
    materias = cargar_carpeta(os.path.join(RUTA_BASE, "conocimiento"))
    admin = cargar_carpeta(os.path.join(RUTA_BASE, "conocimiento_administrativo"))
    secciones = []
    if materias:
        secciones.append("=== CATÁLOGO DE MATERIAS ===\n\n" + materias)
    if admin:
        secciones.append("=== INFORMACIÓN ADMINISTRATIVA Y TRÁMITES ===\n\n" + admin)
    return "\n\n\n".join(secciones)


def cargar_system_prompt():
    """Extrae el SYSTEM_PROMPT del app.py para evaluar exactamente lo que corre en producción."""
    with open(os.path.join(RUTA_BASE, "app.py"), "r", encoding="utf-8") as f:
        codigo = f.read()
    inicio = codigo.index('SYSTEM_PROMPT = """') + len('SYSTEM_PROMPT = """')
    fin = codigo.index('"""', inicio)
    return codigo[inicio:fin]


def main():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: define la variable de entorno GEMINI_API_KEY")
        return

    genai.configure(api_key=api_key)

    print("Cargando base de conocimiento...")
    base = construir_base()
    system_prompt = cargar_system_prompt().format(base_conocimiento=base)

    with open(os.path.join(RUTA_BASE, "evaluacion", "preguntas_prueba.json"), encoding="utf-8") as f:
        data = json.load(f)

    preguntas = data["preguntas"]
    model = genai.GenerativeModel(model_name=MODELO, system_instruction=system_prompt)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    salida = os.path.join(RUTA_BASE, "evaluacion", f"resultados_{timestamp}.md")

    resultados = [f"# Resultados de evaluación — {timestamp}\n"]
    resultados.append(f"Modelo: `{MODELO}` · Total preguntas: {len(preguntas)}\n")
    resultados.append("Revisa cada respuesta y marca: ✅ correcta · ⚠️ mejorable · ❌ alucinación\n\n---\n")

    for p in preguntas:
        print(f"[{p['id']}/{len(preguntas)}] {p['pregunta'][:60]}...")
        try:
            resp = model.generate_content(p["pregunta"]).text
        except Exception as e:
            resp = f"ERROR: {e}"
        time.sleep(1)  # respetar rate limits

        resultados.append(f"## {p['id']}. [{p['categoria']}]\n")
        resultados.append(f"**Pregunta:** {p['pregunta']}\n")
        resultados.append(f"**Se espera:** {p['espera']}\n")
        resultados.append(f"**Respuesta obtenida:**\n\n> {resp}\n")
        resultados.append("**Veredicto:** [ ] ✅  [ ] ⚠️  [ ] ❌\n\n---\n")

    with open(salida, "w", encoding="utf-8") as f:
        f.write("\n".join(resultados))

    print(f"\nListo. Reporte generado en: {salida}")
    print("Revisa manualmente cada respuesta y marca el veredicto.")


if __name__ == "__main__":
    main()

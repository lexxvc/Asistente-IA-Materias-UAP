import streamlit as st
import google.generativeai as genai
import os
import glob
import time

# ─── Configuración de página ───────────────────────────────────────────────
st.set_page_config(
    page_title="Asistente Virtual UAP",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── Detectar modo embed (para iframe en micrositio) ───────────────────────
# El micrositio puede embeber la app con: <iframe src="URL/?embed=true">
EMBED = st.query_params.get("embed", "false").lower() == "true"

# ─── Estilos ────────────────────────────────────────────────────────────────
estilos = """
<style>
    .block-container { max-width: 780px; padding-top: 2rem; }
    .stChatMessage { border-radius: 12px; }
"""
if EMBED:
    # En modo embed se ocultan elementos de Streamlit para integrarse al micrositio
    estilos += """
    header[data-testid="stHeader"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 1rem; }
    """
estilos += "</style>"
st.markdown(estilos, unsafe_allow_html=True)

# ─── Constantes ──────────────────────────────────────────────────────────────
MODELO = "models/gemini-2.5-flash"
MAX_TURNOS_HISTORIAL = 12   # límite de mensajes enviados al modelo (controla costo)
MAX_REINTENTOS = 2

# ─── Carga de base de conocimiento ─────────────────────────────────────────
@st.cache_data(show_spinner="Cargando base de conocimiento...")
def cargar_carpeta(ruta: str) -> str:
    """Lee todos los .md de una carpeta (recursivo) y los concatena."""
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


@st.cache_data(show_spinner=False)
def construir_base_completa() -> str:
    """Une el catálogo de materias y la información administrativa."""
    materias = cargar_carpeta("conocimiento")
    administrativo = cargar_carpeta("conocimiento_administrativo")

    secciones = []
    if materias:
        secciones.append("=== CATÁLOGO DE MATERIAS ===\n\n" + materias)
    if administrativo:
        secciones.append("=== INFORMACIÓN ADMINISTRATIVA Y TRÁMITES ===\n\n" + administrativo)
    return "\n\n\n".join(secciones)


# ─── System prompt ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres el Asistente Virtual de la Universidad Anáhuac Puebla (UAP). Atiendes a alumnos de maestría en dos tipos de consultas:

A) ACADÉMICAS: orientación en la selección de materias y construcción de trayectoria académica.
B) ADMINISTRATIVAS: trámites, servicios escolares, pagos, becas, calendario y procesos institucionales.

REGLAS ESTRICTAS:
1. Responde SOLO con información presente en la base de conocimiento.
2. Si la información no está disponible, di: "Esta información no está disponible en mi base de conocimiento. Te sugiero contactar directamente a servicios escolares de la UAP." — y no inventes nada.
3. Usa lenguaje claro, cercano y orientado a la acción.
4. Sé conciso: máximo 4 párrafos, salvo que el alumno pida una comparación extensa o tabla.
5. Nunca inventes fechas, horarios, docentes, costos, cupos, requisitos ni procedimientos que no estén en la base.
6. Si el alumno pide recomendación de materias y no has recibido su perfil, pregunta primero por:
   - Maestría o programa que cursa
   - Materias ya cursadas
   - Objetivo profesional
   - Preferencia de modalidad (presencial, híbrida, en línea)
   - Intereses principales
7. Cuando recomiendes materias, justifica con criterios explícitos del contexto: área temática, modalidad, nivel técnico, perfil recomendado.
8. Si varias materias aplican, presenta: primera opción, segunda opción y alternativa, con breve justificación.
9. Menciona siempre el área de conocimiento de cada materia que recomiendes.
10. En temas administrativos, indica claramente los pasos y requisitos tal como aparecen en la base. Si un trámite requiere atención presencial o de un área específica, indícalo.
11. No actúes como asesor comercial ni prometas admisiones, inscripciones o resultados de trámites.

BASE DE CONOCIMIENTO:
{base_conocimiento}"""

# ─── Inicialización ─────────────────────────────────────────────────────────
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

if not api_key:
    st.error("⚠️ No se encontró la API key de Gemini. Agrégala en `.streamlit/secrets.toml` o como variable de entorno.")
    st.stop()

genai.configure(api_key=api_key)

base_conocimiento = construir_base_completa()
system_prompt_completo = SYSTEM_PROMPT.format(base_conocimiento=base_conocimiento)

# ─── UI: encabezado ─────────────────────────────────────────────────────────
if not EMBED:
    st.markdown("## 🎓 Asistente Virtual UAP")
    st.markdown("**Universidad Anáhuac Puebla — Maestrías**")
    st.markdown("Resuelvo tus dudas sobre materias, trayectoria académica y trámites administrativos.")
    st.divider()

# ─── Estado de sesión ────────────────────────────────────────────────────────
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# ─── Mostrar historial ───────────────────────────────────────────────────────
for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"], avatar="🎓" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# ─── Preguntas sugeridas (solo al inicio) ───────────────────────────────────
if not st.session_state.mensajes:
    st.markdown("**Puedes empezar con alguna de estas preguntas:**")
    sugerencias = [
        "¿Qué materias hay sobre inteligencia artificial y datos?",
        "¿Qué materia me recomiendas si me interesa el liderazgo?",
        "¿Qué materias tienen modalidad híbrida o en línea?",
        "¿Cómo realizo un trámite administrativo?",
    ]
    cols = st.columns(2)
    for i, sug in enumerate(sugerencias):
        if cols[i % 2].button(sug, key=f"sug_{i}", use_container_width=True):
            st.session_state.pregunta_sugerida = sug
            st.rerun()

# ─── Botón para reiniciar conversación ──────────────────────────────────────
if st.session_state.mensajes:
    if st.button("🔄 Nueva conversación", type="secondary"):
        st.session_state.mensajes = []
        st.rerun()

# ─── Procesar pregunta sugerida ─────────────────────────────────────────────
pregunta_inicial = st.session_state.pop("pregunta_sugerida", None)

# ─── Input del usuario ──────────────────────────────────────────────────────
prompt = st.chat_input("Escribe tu pregunta aquí...") or pregunta_inicial

if prompt:
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Historial limitado a los últimos N turnos (controla costo y contexto)
    mensajes_recientes = st.session_state.mensajes[-MAX_TURNOS_HISTORIAL:]
    historial_gemini = []
    for msg in mensajes_recientes[:-1]:
        rol = "model" if msg["role"] == "assistant" else "user"
        historial_gemini.append({"role": rol, "parts": [msg["content"]]})

    # Llamada a Gemini con streaming y reintentos
    with st.chat_message("assistant", avatar="🎓"):
        placeholder = st.empty()
        respuesta = ""

        for intento in range(MAX_REINTENTOS + 1):
            try:
                model = genai.GenerativeModel(
                    model_name=MODELO,
                    system_instruction=system_prompt_completo,
                )
                chat = model.start_chat(history=historial_gemini)
                stream = chat.send_message(prompt, stream=True)

                respuesta = ""
                for chunk in stream:
                    if chunk.text:
                        respuesta += chunk.text
                        placeholder.markdown(respuesta + "▌")
                placeholder.markdown(respuesta)
                break  # éxito

            except Exception as e:
                if intento < MAX_REINTENTOS:
                    time.sleep(1.5 * (intento + 1))  # backoff
                    continue
                respuesta = (
                    "⚠️ Hubo un problema al generar la respuesta. "
                    "Por favor intenta de nuevo en unos segundos."
                )
                placeholder.markdown(respuesta)

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})

# ─── Footer ─────────────────────────────────────────────────────────────────
if not EMBED:
    st.divider()
    st.caption(
        "Asistente basado en la base de conocimiento oficial de la UAP · "
        "Solo responde con información disponible en el catálogo y documentos institucionales."
    )

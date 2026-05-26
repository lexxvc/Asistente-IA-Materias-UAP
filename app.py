import streamlit as st
import google.generativeai as genai
import os
import glob

# ─── Configuración de página ───────────────────────────────────────────────
st.set_page_config(
    page_title="Simulador de Trayectoria — UAP",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── Estilos ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { max-width: 780px; padding-top: 2rem; }
    .stChatMessage { border-radius: 12px; }
    .st-emotion-cache-1c7y2kd { background: #f0f4ff; }
</style>
""", unsafe_allow_html=True)

# ─── Carga de base de conocimiento ─────────────────────────────────────────
@st.cache_data(show_spinner="Cargando base de conocimiento...")
def cargar_conocimiento(ruta: str = "conocimiento") -> str:
    """
    Lee todos los archivos .md de la carpeta conocimiento/ y los concatena.
    Se ejecuta una sola vez gracias a @st.cache_data.
    """
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

# ─── System prompt ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un asistente académico de la Universidad Anáhuac Puebla (UAP), especializado en orientar a los alumnos de maestría en la selección de materias y construcción de su trayectoria académica.

Tu función es ayudar a los alumnos a identificar qué materias les convienen más según su perfil, objetivos profesionales y disponibilidad, usando únicamente la información de la base de conocimiento proporcionada.

REGLAS ESTRICTAS:
1. Responde SOLO con información presente en la base de conocimiento.
2. Si la información no está disponible, di: "Esta información no está disponible en la base de conocimiento."
3. Usa lenguaje claro, cercano y orientado a decisiones académicas.
4. Sé conciso: máximo 4 párrafos, salvo que el alumno pida una comparación extensa o tabla.
5. Nunca inventes fechas, horarios, docentes, costos, cupos ni prerrequisitos que no estén en la base.
6. Si el alumno pide recomendación de materias y no has recibido su perfil, pregunta primero por:
   - Maestría o programa que cursa
   - Materias ya cursadas
   - Objetivo profesional
   - Preferencia de modalidad (presencial, híbrida, en línea)
   - Intereses principales
7. Cuando recomiendes materias, justifica con criterios explícitos del contexto: área temática, modalidad, nivel técnico, perfil recomendado.
8. Si varias materias aplican, presenta: primera opción, segunda opción y alternativa, con breve justificación.
9. No actúes como asesor comercial ni prometas admisiones o inscripciones.
10. Menciona siempre el área de conocimiento de cada materia que recomiendes.

BASE DE CONOCIMIENTO:
{base_conocimiento}"""

# ─── Inicialización ─────────────────────────────────────────────────────────
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

if not api_key:
    st.error("⚠️ No se encontró la API key de Gemini. Agrégala en `.streamlit/secrets.toml` o como variable de entorno.")
    st.stop()

genai.configure(api_key=api_key)

base_conocimiento = cargar_conocimiento()
system_prompt_completo = SYSTEM_PROMPT.format(base_conocimiento=base_conocimiento)

# ─── UI: encabezado ─────────────────────────────────────────────────────────
st.markdown("## 🎓 Simulador de Trayectoria Académica")
st.markdown("**Universidad Anáhuac Puebla — Maestrías**")
st.markdown("Cuéntame tu perfil o área de interés y te oriento en la elección de materias.")
st.divider()

# ─── Historial de conversación ──────────────────────────────────────────────
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# Mostrar mensajes anteriores
for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"], avatar="🎓" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# ─── Preguntas sugeridas (solo al inicio) ───────────────────────────────────
if not st.session_state.mensajes:
    st.markdown("**Puedes empezar con alguna de estas preguntas:**")
    sugerencias = [
        "¿Qué materias están relacionadas con inteligencia artificial y datos?",
        "¿Qué materias tienen modalidad híbrida o en línea?",
        "¿Qué materia me recomiendas si me interesa el liderazgo?",
        "¿Cuáles son las áreas de conocimiento disponibles?",
    ]
    cols = st.columns(2)
    for i, sug in enumerate(sugerencias):
        if cols[i % 2].button(sug, key=f"sug_{i}", use_container_width=True):
            st.session_state.pregunta_sugerida = sug
            st.rerun()

# ─── Procesar pregunta sugerida ─────────────────────────────────────────────
pregunta_inicial = st.session_state.pop("pregunta_sugerida", None)

# ─── Input del usuario ──────────────────────────────────────────────────────
prompt = st.chat_input("Escribe tu pregunta aquí...") or pregunta_inicial

if prompt:
    # Agregar mensaje del usuario
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Construir historial para Gemini
    historial_gemini = []
    for msg in st.session_state.mensajes[:-1]:  # todos menos el último
        historial_gemini.append({
            "role": msg["role"],
            "parts": [msg["content"]]
        })

    # Llamada a Gemini
    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("Consultando base de conocimiento..."):
            try:
                model = genai.GenerativeModel(
                    model_name="models/gemini-2.5-flash",
                    system_instruction=system_prompt_completo
                )
                chat = model.start_chat(history=historial_gemini)
                response = chat.send_message(prompt)
                respuesta = response.text
            except Exception as e:
                respuesta = f"⚠️ Error al generar la respuesta: {str(e)}"

        st.markdown(respuesta)

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})

# ─── Footer ─────────────────────────────────────────────────────────────────
st.divider()
st.caption("Asistente basado en la base de conocimiento oficial de materias UAP · Solo responde con información disponible en el catálogo.")

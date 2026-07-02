import streamlit as st
import google.generativeai as genai
from google.generativeai import caching
import os
import glob
import time
import uuid
import datetime

# ─── Configuración de página ───────────────────────────────────────────────
st.set_page_config(
    page_title="Asistente Virtual UAP",
    page_icon="🦁",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── Detectar modo embed (para iframe en micrositio) ───────────────────────
EMBED = st.query_params.get("embed", "false").lower() == "true"

# ─── Identidad visual Universidad Anáhuac ───────────────────────────────────
# Naranja PANTONE 151 C → #F38B00 · Café PANTONE 469 C → #6E4A2A
ANAHUAC_NARANJA = "#F38B00"
ANAHUAC_NARANJA_OSC = "#D97A00"
ANAHUAC_CAFE = "#6E4A2A"
ANAHUAC_CAFE_OSC = "#4A3019"

estilos = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Montserrat', sans-serif; }}
    .block-container {{ max-width: 800px; padding-top: 1.5rem; }}
    .uap-header {{
        background: linear-gradient(135deg, {ANAHUAC_NARANJA} 0%, {ANAHUAC_NARANJA_OSC} 100%);
        border-radius: 16px; padding: 1.5rem 1.75rem; margin-bottom: 1.25rem;
        display: flex; align-items: center; gap: 1rem;
        box-shadow: 0 4px 18px rgba(243, 139, 0, 0.25);
    }}
    .uap-logo {{
        width: 56px; height: 56px; background: #fff; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 30px; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }}
    .uap-title h1 {{ font-size: 1.35rem; font-weight: 700; margin: 0; line-height: 1.2; color: #fff; }}
    .uap-title p {{ font-size: 0.85rem; margin: 2px 0 0; opacity: 0.95; color: #fff; }}
    .stChatMessage {{ border-radius: 14px; }}
    .stButton button {{
        border-radius: 10px; border: 1.5px solid {ANAHUAC_NARANJA};
        color: {ANAHUAC_CAFE_OSC}; background: #fff; font-weight: 500;
        transition: all 0.15s ease;
    }}
    .stButton button:hover {{ background: {ANAHUAC_NARANJA}; color: #fff; }}
    [data-testid="stChatInput"]:focus-within {{ border-color: {ANAHUAC_NARANJA} !important; }}
    .uap-footer {{
        font-size: 0.78rem; color: {ANAHUAC_CAFE}; text-align: center;
        margin-top: 1.5rem; opacity: 0.85;
    }}
    .uap-footer strong {{ color: {ANAHUAC_CAFE_OSC}; }}
    .sug-label {{ color: {ANAHUAC_CAFE_OSC}; font-weight: 600; font-size: 0.92rem; margin-bottom: 0.4rem; }}
"""
if EMBED:
    estilos += """
    header[data-testid="stHeader"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 1rem; }
    """
estilos += "</style>"
st.markdown(estilos, unsafe_allow_html=True)

# ─── Constantes de configuración ─────────────────────────────────────────────
MODELO = "models/gemini-2.5-flash"
MAX_TURNOS_HISTORIAL = 12       # mensajes máximos enviados al modelo
MAX_REINTENTOS = 2
MAX_PREGUNTAS_SESION = 20       # límite anti-abuso por sesión
CACHE_TTL_MINUTOS = 60          # vida del caché de contexto de Gemini
USAR_CACHE = True               # poner False para desactivar caché explícito

# ─── Carga de base de conocimiento ─────────────────────────────────────────
@st.cache_data(show_spinner="Cargando base de conocimiento...")
def cargar_carpeta(ruta: str) -> str:
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
    materias = cargar_carpeta("conocimiento")
    administrativo = cargar_carpeta("conocimiento_administrativo")
    secciones = []
    if materias:
        secciones.append("=== CATÁLOGO DE MATERIAS ===\n\n" + materias)
    if administrativo:
        secciones.append("=== INFORMACIÓN ADMINISTRATIVA Y TRÁMITES ===\n\n" + administrativo)
    return "\n\n\n".join(secciones)


@st.cache_data(show_spinner=False)
def listar_areas() -> list:
    """Lista las áreas de conocimiento a partir de las carpetas."""
    carpetas = [d for d in glob.glob("conocimiento/*/") if "README" not in d]
    areas = sorted(os.path.basename(c.rstrip("/")).replace("_", " ").title() for c in carpetas)
    return areas


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
12. La orientación que das es informativa, no vinculante ni oficial.

BASE DE CONOCIMIENTO:
{base_conocimiento}"""

# ─── Inicialización ─────────────────────────────────────────────────────────
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
if not api_key:
    st.error("⚠️ No se encontró la API key de Gemini. Agrégala en `.streamlit/secrets.toml`.")
    st.stop()

genai.configure(api_key=api_key)

base_conocimiento = construir_base_completa()
system_prompt_completo = SYSTEM_PROMPT.format(base_conocimiento=base_conocimiento)

# ─── Caché de contexto de Gemini (ahorro ~90% en tokens de entrada) ─────────
# La base de conocimiento (~100k tokens) se sube UNA vez al caché de Google.
# Las siguientes consultas leen del caché a ~10% del precio de entrada normal.
# El caché expira tras CACHE_TTL_MINUTOS sin recrearse (no cobra storage si expira).
@st.cache_resource(ttl=(CACHE_TTL_MINUTOS - 5) * 60, show_spinner=False)
def obtener_cache_contexto():
    """Crea (o renueva) el caché de contexto compartido por todos los usuarios."""
    try:
        cache = caching.CachedContent.create(
            model=MODELO,
            display_name="base_conocimiento_uap",
            system_instruction=system_prompt_completo,
            ttl=datetime.timedelta(minutes=CACHE_TTL_MINUTOS),
        )
        return cache
    except Exception:
        return None  # fallback: modo sin caché


def crear_modelo():
    """Devuelve el modelo, usando caché de contexto si está disponible."""
    if USAR_CACHE:
        cache = obtener_cache_contexto()
        if cache is not None:
            try:
                return genai.GenerativeModel.from_cached_content(cached_content=cache)
            except Exception:
                pass
    # Fallback sin caché
    return genai.GenerativeModel(model_name=MODELO, system_instruction=system_prompt_completo)


# ─── Registro de preguntas en Google Sheets (opcional) ───────────────────────
# Se configura en secrets: [gcp_service_account] (JSON) + GSHEET_URL.
# Si no está configurado, la app funciona igual sin registrar nada.
@st.cache_resource(show_spinner=False)
def obtener_hoja():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        if "gcp_service_account" not in st.secrets or "GSHEET_URL" not in st.secrets:
            return None
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(st.secrets["GSHEET_URL"])
        return sh.sheet1
    except Exception:
        return None


def log_evento(tipo: str, pregunta: str = "", respuesta: str = "", feedback: str = ""):
    """Registra un evento en la hoja del administrador. Nunca rompe la app."""
    try:
        ws = obtener_hoja()
        if ws is None:
            return
        ws.append_row([
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            st.session_state.session_id,
            tipo,
            pregunta[:500],
            respuesta[:800],
            feedback,
            st.session_state.get("maestria", ""),
        ])
    except Exception:
        pass


# ─── Header institucional ────────────────────────────────────────────────────
st.markdown(f"""
<div class="uap-header">
    <div class="uap-logo">🦁</div>
    <div class="uap-title">
        <h1>Asistente Virtual UAP</h1>
        <p>Universidad Anáhuac Puebla · Orientación académica y administrativa</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Aviso de privacidad y disclaimer ────────────────────────────────────────
with st.expander("ℹ️ Aviso de uso y privacidad"):
    st.markdown("""
**Aviso importante:**
- Este asistente proporciona **orientación informativa** basada en el catálogo oficial de materias
  y documentos institucionales de la Universidad Anáhuac Puebla. **No constituye información
  oficial vinculante** ni sustituye la asesoría de servicios escolares.
- Para trámites oficiales, inscripciones y confirmación de fechas o requisitos, acude
  directamente a **servicios escolares de la UAP**.
- Las preguntas realizadas pueden registrarse de forma anónima con fines de mejora del servicio.
  No escribas datos personales sensibles (contraseñas, datos bancarios, información médica).
- Las respuestas son generadas por inteligencia artificial y pueden contener imprecisiones.
""")

# ─── Estado de sesión ────────────────────────────────────────────────────────
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "n_preguntas" not in st.session_state:
    st.session_state.n_preguntas = 0
if "feedback_dado" not in st.session_state:
    st.session_state.feedback_dado = set()

# ─── Selector de maestría (punto 10) ────────────────────────────────────────
if not st.session_state.mensajes:
    areas = listar_areas()
    opciones = ["Prefiero no especificar"] + areas + ["Otra"]
    seleccion = st.selectbox(
        "🎓 ¿En qué área está tu maestría? (opcional, mejora las recomendaciones)",
        opciones,
        key="selector_area",
    )
    if seleccion == "Otra":
        otra = st.text_input("Escribe tu maestría o área:", key="otra_maestria")
        st.session_state.maestria = otra.strip()
    elif seleccion != "Prefiero no especificar":
        st.session_state.maestria = seleccion
    else:
        st.session_state.maestria = ""

# ─── Mostrar historial + feedback por respuesta ──────────────────────────────
for i, msg in enumerate(st.session_state.mensajes):
    avatar = "🦁" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        # Feedback 👍/👎 en cada respuesta del asistente
        if msg["role"] == "assistant":
            fb = st.feedback("thumbs", key=f"fb_{i}")
            if fb is not None and i not in st.session_state.feedback_dado:
                st.session_state.feedback_dado.add(i)
                valor = "positivo" if fb == 1 else "negativo"
                pregunta_previa = st.session_state.mensajes[i-1]["content"] if i > 0 else ""
                log_evento("feedback", pregunta_previa, msg["content"], valor)
                st.toast("¡Gracias por tu retroalimentación!", icon="🙌")

# ─── Preguntas sugeridas (solo al inicio) ───────────────────────────────────
if not st.session_state.mensajes:
    st.markdown('<p class="sug-label">Puedes empezar con alguna de estas preguntas:</p>', unsafe_allow_html=True)
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
        st.session_state.feedback_dado = set()
        st.rerun()

# ─── Límite de preguntas por sesión (anti-abuso) ────────────────────────────
limite_alcanzado = st.session_state.n_preguntas >= MAX_PREGUNTAS_SESION
if limite_alcanzado:
    st.warning(
        f"Has alcanzado el límite de {MAX_PREGUNTAS_SESION} preguntas por sesión. "
        "Recarga la página para iniciar una nueva sesión, o contacta a servicios "
        "escolares si necesitas más apoyo."
    )

# ─── Procesar pregunta sugerida ─────────────────────────────────────────────
pregunta_inicial = st.session_state.pop("pregunta_sugerida", None)

# ─── Input del usuario ──────────────────────────────────────────────────────
prompt = None
if not limite_alcanzado:
    prompt = st.chat_input("Escribe tu pregunta aquí...") or pregunta_inicial

if prompt:
    st.session_state.n_preguntas += 1
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Perfil del alumno (se inyecta en el mensaje, no en el system prompt,
    # para no invalidar el caché de contexto compartido)
    maestria = st.session_state.get("maestria", "")
    prompt_para_modelo = prompt
    if maestria:
        prompt_para_modelo = f"[Contexto: el alumno cursa una maestría del área de {maestria}]\n\n{prompt}"

    mensajes_recientes = st.session_state.mensajes[-MAX_TURNOS_HISTORIAL:]
    historial_gemini = []
    for msg in mensajes_recientes[:-1]:
        rol = "model" if msg["role"] == "assistant" else "user"
        historial_gemini.append({"role": rol, "parts": [msg["content"]]})

    with st.chat_message("assistant", avatar="🦁"):
        placeholder = st.empty()
        respuesta = ""

        for intento in range(MAX_REINTENTOS + 1):
            try:
                model = crear_modelo()
                chat = model.start_chat(history=historial_gemini)
                stream = chat.send_message(prompt_para_modelo, stream=True)

                respuesta = ""
                for chunk in stream:
                    if chunk.text:
                        respuesta += chunk.text
                        placeholder.markdown(respuesta + "▌")
                placeholder.markdown(respuesta)
                break
            except Exception:
                if intento < MAX_REINTENTOS:
                    time.sleep(1.5 * (intento + 1))
                    continue
                respuesta = (
                    "⚠️ Hubo un problema al generar la respuesta. "
                    "Por favor intenta de nuevo en unos segundos."
                )
                placeholder.markdown(respuesta)

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
    log_evento("pregunta", prompt, respuesta)
    st.rerun()  # re-render para mostrar el widget de feedback

# ─── Footer ─────────────────────────────────────────────────────────────────
if not EMBED:
    st.markdown(
        '<div class="uap-footer">Asistente basado en la base de conocimiento oficial de la '
        '<strong>Universidad Anáhuac Puebla</strong>. Orientación informativa, no vinculante.<br>'
        'Para trámites oficiales acude a servicios escolares y siempre acude a tu coordinador académico para aclarar dudas.</div>',
        unsafe_allow_html=True
    )

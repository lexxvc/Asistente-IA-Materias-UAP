import streamlit as st
from google import genai
from google.genai import types
import os
import time
import uuid
import datetime

import base_conocimiento as bc

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
MODELO_DEFAULT = "gemini-3.8-flash"   # se puede cambiar con el secret GEMINI_MODEL
MAX_TURNOS_HISTORIAL = 12       # mensajes máximos enviados al modelo
MAX_REINTENTOS = 3              # reintentos ante saturación del modelo (503) o fallas temporales
MAX_PREGUNTAS_SESION = 20       # límite anti-abuso por sesión
CACHE_TTL_MINUTOS = 60          # vida del caché de contexto de Gemini
USAR_CACHE = True               # poner False para desactivar caché explícito
MOSTRAR_TOKENS = True           # contador de tokens bajo el cuadro de pregunta
MOSTRAR_ERRORES = True          # muestra el detalle técnico del error (poner False en producción)

# ─── Carga de base de conocimiento ─────────────────────────────────────────
# Toda la lógica (índice general, fichas, system prompt, contexto de fecha)
# vive en base_conocimiento.py, compartida con la evaluación.
@st.cache_data(show_spinner="Cargando base de conocimiento...")
def obtener_system_prompt() -> str:
    return bc.system_prompt_completo()


@st.cache_data(show_spinner=False)
def listar_maestrias() -> list:
    return bc.listar_maestrias(bc.cargar_fichas())


# ─── Inicialización ─────────────────────────────────────────────────────────
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
if not api_key:
    st.error("⚠️ No se encontró la API key de Gemini. Agrégala en `.streamlit/secrets.toml`.")
    st.stop()

@st.cache_resource(show_spinner=False)
def obtener_cliente(key: str) -> genai.Client:
    # Por defecto usa la API de Gemini (Google AI Studio).
    # Solo para keys de Vertex AI (modo express): secret GEMINI_VERTEX = "true".
    vertex = str(st.secrets.get("GEMINI_VERTEX", os.environ.get("GEMINI_VERTEX", ""))).lower() == "true"
    return genai.Client(api_key=key, vertexai=True) if vertex else genai.Client(api_key=key)


cliente = obtener_cliente(api_key)
MODELO = str(st.secrets.get("GEMINI_MODEL", os.environ.get("GEMINI_MODEL", MODELO_DEFAULT)))
# Modelo de respaldo opcional (secret GEMINI_MODEL_RESPALDO): se usa en el último
# intento si el principal sigue saturado (503).
MODELO_RESPALDO = str(st.secrets.get("GEMINI_MODEL_RESPALDO", os.environ.get("GEMINI_MODEL_RESPALDO", ""))).strip()

system_prompt_completo = obtener_system_prompt()

# ─── Caché de contexto de Gemini (ahorro ~90% en tokens de entrada) ─────────
# La base de conocimiento (~55k tokens: índice + 81 fichas) se sube UNA vez al caché de Google.
# Las siguientes consultas leen del caché a ~10% del precio de entrada normal.
# El caché expira tras CACHE_TTL_MINUTOS sin recrearse (no cobra storage si expira).
# En el tier GRATUITO el caché explícito no está permitido (límite 0): la app lo
# detecta, deja de intentarlo y sigue sin él. Gemini aplica además caché IMPLÍCITO
# automático a prompts grandes y repetidos (se ve en el contador como "caché").
@st.cache_resource(show_spinner=False)
def _estado_cache() -> dict:
    return {"deshabilitado": False}


def _es_error_de_cuota_de_cache(e: Exception) -> bool:
    t = str(e)
    return "429" in t or "RESOURCE_EXHAUSTED" in t or "FreeTier" in t or "limit=0" in t


@st.cache_resource(ttl=(CACHE_TTL_MINUTOS - 5) * 60, show_spinner=False)
def obtener_cache_contexto():
    """Crea (o renueva) el caché de contexto compartido por todos los usuarios.

    Devuelve el nombre del caché (p. ej. "cachedContents/abc123") o None.
    """
    try:
        cache = cliente.caches.create(
            model=MODELO,
            config=types.CreateCachedContentConfig(
                display_name="base_conocimiento_uap",
                system_instruction=system_prompt_completo,
                ttl=f"{CACHE_TTL_MINUTOS * 60}s",
            ),
        )
        return cache.name
    except Exception as e:
        if _es_error_de_cuota_de_cache(e):
            _estado_cache()["deshabilitado"] = True
            print("[Asistente UAP] caché explícito no disponible en este plan "
                  "(tier gratuito): se desactiva y se usa el modo sin caché.", flush=True)
        else:
            print(f"[Asistente UAP] sin caché de contexto: {type(e).__name__}: {e}", flush=True)
        return None  # fallback: modo sin caché


def configuracion_modelo() -> types.GenerateContentConfig:
    """Usa el caché de contexto si está disponible; si no, manda el system prompt."""
    if USAR_CACHE and not _estado_cache()["deshabilitado"]:
        nombre_cache = obtener_cache_contexto()
        if nombre_cache:
            return types.GenerateContentConfig(cached_content=nombre_cache)
    return types.GenerateContentConfig(system_instruction=system_prompt_completo)


def _es_saturacion(e: Exception) -> bool:
    t = str(e)
    return "503" in t or "UNAVAILABLE" in t or "overloaded" in t.lower() or "high demand" in t


def _es_error_de_cache(e: Exception) -> bool:
    t = str(e).lower()
    return "cachedcontent" in t or "cached content" in t or "cachedcontents/" in t


# ─── Conteo de tokens ───────────────────────────────────────────────────────
def leer_uso(usage) -> dict:
    """Convierte el usage_metadata de Gemini (llega en el último chunk del stream)."""
    if usage is None:
        return {}
    return {
        "entrada": usage.prompt_token_count or 0,
        "cache": usage.cached_content_token_count or 0,
        "salida": usage.candidates_token_count or 0,
        # Gemini "piensa" antes de responder; esos tokens se cobran como salida
        "razonamiento": usage.thoughts_token_count or 0,
    }


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def texto_uso(u: dict) -> str:
    if not u:
        return ""
    partes = [f"⬆️ Entrada {_fmt(u['entrada'])}"]
    if u["cache"]:
        partes[0] += f" (caché {_fmt(u['cache'])})"
    partes.append(f"⬇️ Salida {_fmt(u['salida'])}")
    if u["razonamiento"]:
        partes.append(f"🧠 Razonamiento {_fmt(u['razonamiento'])}")
    return " · ".join(partes)


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
if "tokens_sesion" not in st.session_state:
    st.session_state.tokens_sesion = {"entrada": 0, "cache": 0, "salida": 0, "razonamiento": 0}

# ─── Selector de maestría ───────────────────────────────────────────────────
# Se pide la maestría (no el área): la obligatoriedad de materias depende de ella.
if not st.session_state.mensajes:
    opciones = ["Prefiero no especificar"] + listar_maestrias() + ["Otra"]
    seleccion = st.selectbox(
        "🎓 ¿Qué maestría cursas? (opcional, mejora las recomendaciones)",
        opciones,
        key="selector_maestria",
    )
    if seleccion == "Otra":
        otra = st.text_input("Escribe tu maestría:", key="otra_maestria")
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
        if MOSTRAR_ERRORES and msg.get("error"):
            st.code(msg["error"][:1500], language=None)
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
        "¿Qué materias son obligatorias para mi maestría?",
        "¿Qué materias puedo cursar en línea?",
        "¿Qué materias abren el próximo periodo?",
    ]
    if bc.hay_base_administrativa():
        sugerencias.append("¿Cómo realizo un trámite administrativo?")
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
        st.session_state.tokens_sesion = {"entrada": 0, "cache": 0, "salida": 0, "razonamiento": 0}
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

    # Fecha, periodo en curso y maestría (se inyectan en el mensaje, no en el
    # system prompt, para no invalidar el caché de contexto compartido)
    prompt_para_modelo = bc.contexto_mensaje(prompt, st.session_state.get("maestria", ""))

    mensajes_recientes = st.session_state.mensajes[-MAX_TURNOS_HISTORIAL:]
    historial_gemini = []
    for msg in mensajes_recientes[:-1]:
        rol = "model" if msg["role"] == "assistant" else "user"
        historial_gemini.append(types.Content(role=rol, parts=[types.Part(text=msg["content"])]))

    with st.chat_message("assistant", avatar="🦁"):
        placeholder = st.empty()
        respuesta = ""
        uso = {}
        error = ""

        saturado = False
        for intento in range(MAX_REINTENTOS + 1):
            ultimo = intento == MAX_REINTENTOS
            # En el último intento, si el principal sigue saturado, se usa el respaldo
            modelo = MODELO_RESPALDO if (ultimo and saturado and MODELO_RESPALDO) else MODELO
            # El caché pertenece al modelo principal; con el respaldo va sin caché
            config = (configuracion_modelo() if modelo == MODELO
                      else types.GenerateContentConfig(system_instruction=system_prompt_completo))
            try:
                chat = cliente.chats.create(model=modelo, config=config, history=historial_gemini)
                respuesta = ""
                usage = None
                for chunk in chat.send_message_stream(prompt_para_modelo):
                    if chunk.text:
                        respuesta += chunk.text
                        placeholder.markdown(respuesta + "▌")
                    if chunk.usage_metadata is not None:
                        usage = chunk.usage_metadata
                placeholder.markdown(respuesta)
                uso = leer_uso(usage)
                error = ""
                break
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                print(f"[Asistente UAP] intento {intento + 1} ({modelo}): {error}", flush=True)
                saturado = _es_saturacion(e)
                # Solo si el error es del caché (expiró o es inválido) se recrea
                if _es_error_de_cache(e):
                    obtener_cache_contexto.clear()
                if not ultimo:
                    # Espera creciente: 2, 4, 8 s (la saturación suele ser momentánea)
                    time.sleep(2 ** (intento + 1))
                    continue
                respuesta = (
                    "⚠️ El servicio de IA está saturado en este momento. "
                    "Por favor intenta de nuevo en un minuto."
                    if saturado else
                    "⚠️ Hubo un problema al generar la respuesta. "
                    "Por favor intenta de nuevo en unos segundos."
                )
                placeholder.markdown(respuesta)


    st.session_state.mensajes.append({"role": "assistant", "content": respuesta, "uso": uso, "error": error})
    for k in st.session_state.tokens_sesion:
        st.session_state.tokens_sesion[k] += uso.get(k, 0)
    log_evento("pregunta", prompt, respuesta)
    st.rerun()  # re-render para mostrar el widget de feedback

# ─── Contador de tokens (bajo el cuadro de pregunta) ────────────────────────
if MOSTRAR_TOKENS:
    ultimo = next((m.get("uso") for m in reversed(st.session_state.mensajes)
                   if m["role"] == "assistant" and m.get("uso")), None)
    if ultimo:
        t = st.session_state.tokens_sesion
        linea = (f"**Última pregunta:** {texto_uso(ultimo)}  \n"
                 f"**Sesión:** ⬆️ {_fmt(t['entrada'])} · ⬇️ {_fmt(t['salida'] + t['razonamiento'])}")
        # Zona fija bajo el chat_input: st.bottom (Streamlit reciente) o _bottom (versiones previas)
        destino = getattr(st, "bottom", None) or getattr(st, "_bottom", None)
        (destino.caption if destino is not None else st.caption)(linea)

# ─── Footer ─────────────────────────────────────────────────────────────────
if not EMBED:
    st.markdown(
        '<div class="uap-footer">Asistente basado en la base de conocimiento oficial de la '
        '<strong>Universidad Anáhuac Puebla</strong>. Orientación informativa, no vinculante.<br>'
        'Para trámites oficiales acude a servicios escolares y siempre acude a tu coordinador académico para aclarar dudas.</div>',
        unsafe_allow_html=True
    )

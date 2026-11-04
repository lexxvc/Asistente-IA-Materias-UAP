# Guía de configuración — Asistente Virtual UAP

## 1. Secrets necesarios

En Streamlit Community Cloud: **Settings → Secrets**. En local: `.streamlit/secrets.toml`

```toml
GEMINI_API_KEY = "AIza..."

# ─── OPCIONAL: registro de preguntas en Google Sheets ───
GSHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_DE_HOJA/edit"

[gcp_service_account]
type = "service_account"
project_id = "tu-proyecto"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "asistente-uap@tu-proyecto.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Si no configuras la sección de Google Sheets, la app funciona normal sin registrar nada.

---

## 2. Configurar el registro en Google Drive del administrador

El registro usa una **cuenta de servicio de Google** (no tu contraseña personal).
Funciona así: la cuenta de servicio es un "robot" con su propio correo; el administrador
comparte su hoja de cálculo con ese correo y la app escribe ahí.

### Pasos (una sola vez, ~10 minutos)

1. Ve a [console.cloud.google.com](https://console.cloud.google.com) con la cuenta del administrador
2. Crea un proyecto nuevo (ej. "asistente-uap")
3. En **APIs y servicios → Biblioteca**, habilita **Google Sheets API**
4. En **APIs y servicios → Credenciales → Crear credenciales → Cuenta de servicio**
   - Nombre: `asistente-uap` → Crear → omite los roles opcionales → Listo
5. Entra a la cuenta de servicio creada → pestaña **Claves** → **Agregar clave → JSON**
   - Se descarga un archivo `.json` — su contenido va en la sección `[gcp_service_account]` de los secrets
6. Crea una hoja de cálculo en el Google Drive del administrador con estos encabezados en la fila 1:
   `fecha | session_id | tipo | pregunta | respuesta | feedback | maestria`
7. Comparte la hoja (botón Compartir) con el correo de la cuenta de servicio
   (algo como `asistente-uap@tu-proyecto.iam.gserviceaccount.com`) con permiso de **Editor**
8. Copia la URL de la hoja en `GSHEET_URL` de los secrets

### Cómo cambiar la cuenta del administrador

No hace falta crear nada nuevo. El nuevo administrador solo debe:

1. Crear su propia hoja de cálculo con los mismos encabezados
2. Compartirla con el mismo correo de la cuenta de servicio (permiso Editor)
3. Actualizar `GSHEET_URL` en los secrets de Streamlit → la app redeploya sola

Si además quieren desvincular al administrador anterior por completo, se crea una cuenta
de servicio nueva (pasos 4-5) y se reemplaza toda la sección `[gcp_service_account]`.

---

## 3. Evitar el cold start (app dormida)

Streamlit Community Cloud duerme la app tras ~12 horas sin visitas y tarda ~30 segundos
en despertar. Para mantenerla activa en horario de alumnos:

### Opción recomendada: cron-job.org (gratis)

1. Crea cuenta en [cron-job.org](https://cron-job.org)
2. **Create cronjob**:
   - URL: la URL pública de tu app (ej. `https://asistente-uap.streamlit.app`)
   - Intervalo: cada **10 minutos**
   - Horario: restringe a horario útil, ej. lunes-sábado de 7:00 a 22:00
     (así no consumes recursos de madrugada y dejas dormir la app)
3. Guardar. Listo.

### Alternativa: UptimeRobot (gratis)

Mismo concepto: monitor HTTP(s) a tu URL cada 5 minutos. Además te avisa por
correo si la app se cae — doble beneficio (keep-alive + monitoreo).

> Nota: mantener la app despierta 24/7 con pings es aceptable para un servicio
> institucional real, pero revisa periódicamente los términos del plan gratuito
> de Streamlit por si cambian.

---

## 4. Correr la evaluación de calidad

Antes de publicar cualquier cambio de prompt, modelo o base de conocimiento:

```bash
export GEMINI_API_KEY="tu_key"      # en Windows: set GEMINI_API_KEY=tu_key
python evaluacion/eval_preguntas.py           # todas
python evaluacion/eval_preguntas.py 10 26 28  # solo algunas, por id
```

Usa exactamente el mismo prompt, índice y contexto de fecha que producción
(`base_conocimiento.py`). Genera `evaluacion/resultados_FECHA.md` con las 30
preguntas, una tabla resumen y el resultado de las **verificaciones automáticas**
(✅ pasa / ❌ falla / 👁️ revisión manual). El script termina con código de error
si alguna verificación falla.

Las verificaciones se definen por pregunta en `preguntas_prueba.json`:
`debe_contener`, `debe_contener_alguno` y `no_debe_contener` (sin distinguir
mayúsculas ni acentos). También se puede simular la maestría (`maestria`) y una
conversación previa (`historial`).

Las verificaciones solo buscan palabras clave, así que revisa también cada
respuesta y márcala:
- ✅ correcta
- ⚠️ mejorable
- ❌ alucinación (fallo crítico — NO publicar hasta corregir)

Las preguntas 18-20 son "trampas" diseñadas para detectar alucinaciones: el
asistente NUNCA debe confirmar costos, horarios o docentes que no están en la base.

---

## 5. Parámetros ajustables (inicio de app.py)

| Constante | Default | Qué controla |
|---|---|---|
| `MODELO` | gemini-2.5-flash | Modelo de Gemini |
| `MAX_PREGUNTAS_SESION` | 20 | Límite anti-abuso por sesión |
| `MAX_TURNOS_HISTORIAL` | 12 | Mensajes enviados al modelo |
| `CACHE_TTL_MINUTOS` | 60 | Vida del caché de contexto |
| `USAR_CACHE` | True | Activa/desactiva caché explícito |
| `MOSTRAR_TOKENS` | True | Contador de tokens bajo el cuadro de pregunta (ponlo en False para alumnos) |

### Nota sobre el caché de contexto

El caché reduce ~90% el costo de tokens de entrada, pero Google cobra
almacenamiento (~$1 USD por millón de tokens por hora mientras el caché viva).
Con la base actual (~55k tokens) el storage cuesta ~$0.06 USD/hora activa.

- **Con tráfico constante** (varias consultas por hora): el caché AHORRA mucho.
- **Con tráfico muy bajo** (pocas consultas al día): puede costar más de lo que ahorra
  → poner `USAR_CACHE = False`.

El caché expira solo tras `CACHE_TTL_MINUTOS` sin renovarse, así que en periodos
sin uso no genera costo.

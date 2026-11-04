# 🎓 Asistente IA — Materias UAP

> Simulador de Trayectoria Académica para alumnos de maestría de la Universidad Anáhuac Puebla.

Asistente conversacional basado en inteligencia artificial que orienta a los estudiantes en la **selección de materias** y construcción de su **trayectoria académica**, respondiendo únicamente con información del catálogo oficial de la universidad.

---

## ✨ Características

- 💬 **Chat conversacional** con memoria de sesión — entiende preguntas de seguimiento
- 📚 **81 materias** organizadas en 15 áreas de conocimiento
- 🗂️ **Índice general automático** — tabla con clave, área, obligatoriedad, modalidad, nivel y aperturas de todas las materias, generada de las fichas en cada arranque
- 🎓 **Selector de maestría** — el asistente sabe qué materias son obligatorias para el alumno
- 📅 **Consciente de la fecha** — distingue aperturas pasadas de futuras
- ⚡ **Contexto completo + caché de Gemini** — sin vector DB ni embeddings
- 🔢 **Contador de tokens** — entrada (y cuánto vino del caché), salida y razonamiento por pregunta y por sesión, bajo el cuadro de pregunta (`MOSTRAR_TOKENS`)
- 👍 **Feedback por respuesta** y registro opcional de preguntas en Google Sheets
- 🛡️ **Límite de 20 preguntas por sesión** (anti-abuso)
- 🖼️ **Modo embed** para iframe en el micrositio (`?embed=true`)
- 🧪 **Evaluación con verificaciones automáticas** (30 preguntas)
- 🔒 **Respuestas acotadas** al catálogo oficial — nunca inventa información
- 🚀 **Deploy en un clic** vía Streamlit Community Cloud

---

## 🗂️ Estructura del proyecto

```
Asistente-IA-Materias-UAP/
├── app.py                          ← Aplicación Streamlit (interfaz)
├── base_conocimiento.py            ← Carga de fichas, índice general, system prompt y contexto de fecha
├── requirements.txt
├── evaluacion/
│   ├── preguntas_prueba.json       ← 30 preguntas con verificaciones automáticas
│   └── eval_preguntas.py
├── .gitignore
├── .streamlit/
│   └── secrets.toml                ← API key (NO subir a GitHub)
└── conocimiento/
    ├── README.md
    ├── CIENCIA_DE_DATOS_E_INTELIGENCIA_ARTIFICIAL/
    │   ├── ITI55701_Inteligencia_artificial.md
    │   ├── ITI55703_Machine_learning.md
    │   └── ...
    ├── DIRECCION_Y_LIDERAZGO/
    ├── ECONOMIA_Y_FINANZAS/
    └── ...  (15 áreas en total)
```

---

## 🧠 Áreas de conocimiento

| Área | Materias |
|------|----------|
| Administración y Gestión Pública | 5 |
| Análisis e Inteligencia de Negocios | 5 |
| Ciencia de Datos e Inteligencia Artificial | 7 |
| Comunicación | 5 |
| Derecho Empresarial | 6 |
| Dirección y Liderazgo | 6 |
| Economía y Finanzas | 6 |
| Fundamentos y Hospitalidad en la Salud | 5 |
| Ingeniería y Operaciones | 5 |
| Innovación Tecnológica y Emprendimiento | 4 |
| Mercadotecnia | 7 |
| Planeación y Estrategia | 5 |
| Seminarios y Tesis | 2 |
| Talento Humano y Organizacional | 6 |
| Toma de Decisiones | 7 |
| **Total** | **81** |

---

## ⚙️ Cómo funciona

```
Fichas .md (81)  ──►  base_conocimiento.py
                        ├─ ÍNDICE GENERAL (tabla resumen + obligatorias por maestría + materias en línea)
                        └─ FICHAS DETALLADAS
                                │
                                ▼
          System prompt + base (~55k tokens) → caché de contexto de Gemini
                                │
Pregunta + [fecha, periodo en curso, maestría] ──►  Gemini 2.5 Flash
                                │
                                ▼
                 Respuesta acotada al catálogo oficial
```

La base completa cabe en el contexto del modelo, así que se envía entera (sin
fragmentar ni recuperar por similitud). Esto evita que una búsqueda omita
materias relevantes. Para que no se cobre en cada pregunta, se sube una sola
vez al **caché de contexto** de Gemini y las consultas la leen a ~10% del precio.

El **índice general** se genera en cada arranque a partir de las fichas, así que
nunca queda desactualizado: basta con editar las fichas. Resuelve las preguntas
agregadas ("¿qué materias son en línea?", "¿cuáles son obligatorias para mi
maestría?") sin que el modelo tenga que recorrer las 81 fichas.

La fecha, el periodo en curso y la maestría elegida van en cada mensaje (no en el
system prompt) para no invalidar el caché compartido.

---

## 🚀 Deploy en Streamlit Community Cloud

### 1. Obtener la API key de Gemini (gratis)

1. Ve a [aistudio.google.com](https://aistudio.google.com)
2. Inicia sesión con tu cuenta de Google
3. Clic en **Get API Key** → **Create API key**
4. Copia la key

### 2. Subir a GitHub

Asegúrate de que el archivo `.streamlit/secrets.toml` esté en el `.gitignore` (ya incluido). Sube el repositorio normalmente.

### 3. Deploy

1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Conecta tu cuenta de GitHub
3. Selecciona este repositorio y el archivo `app.py`
4. En **Settings → Secrets**, agrega:

```toml
GEMINI_API_KEY = "AIza..."
```

5. Haz clic en **Deploy** — listo en ~2 minutos ✅

La URL pública generada es la que se integra en el micrositio.

---

## 💻 Correr localmente

```bash
# Clonar el repositorio
git clone https://github.com/lexxvc/Asistente-IA-Materias-UAP.git
cd Asistente-IA-Materias-UAP

# Instalar dependencias
pip install -r requirements.txt

# Crear archivo de secrets
mkdir -p .streamlit
echo 'GEMINI_API_KEY = "tu_api_key_aqui"' > .streamlit/secrets.toml

# Correr la app
streamlit run app.py
```

---

## 📦 Dependencias

```
streamlit>=1.40.0
google-genai>=1.0.0      ← SDK oficial actual de Gemini
gspread>=6.0.0        ← opcional, registro de preguntas en Google Sheets
google-auth>=2.0.0
```

Sin bases de datos vectoriales ni Docker.

---

## 📁 Actualizar la base de conocimiento

Los documentos son archivos Markdown planos — uno por materia. Para agregar o editar materias:

1. Edita o crea el archivo `.md` correspondiente en `conocimiento/<ÁREA>/`
2. Haz commit y push a GitHub
3. Streamlit Community Cloud redeploya automáticamente

**Formato recomendado para cada MD:**

```markdown
# Nombre de la Materia

> **Clave:** ABC55700 · **Área de conocimiento:** NOMBRE DEL ÁREA

## 📋 Información general
| Campo | Detalle |
|---|---|
| **Clave** | ABC55700 |
| **Nombre** | Nombre de la Materia |
| **Área de conocimiento** | Nombre del área |
| **Obligatoria** | ✅ Sí / ❌ No |
| **Obligatoria para** | Ninguna maestría / Todas las maestrías / Maestría en X; Maestría en Y |
| **Periodo de apertura** | Cada año en Otoño (agosto – diciembre). Ciclos programados 2026–2029: Otoño 2026, Otoño 2027. |
| **Nivel técnico** | Básico / Intermedio / Avanzado |
| **Modalidad** | Híbrida / Virtual / Asíncrona |
| **Horas fuera de clase / semana** | 3 |

## 📝 Descripción
...

## 🎯 Aprendizajes clave
...
```

**Reglas para que el índice general salga bien:**
- Respeta los nombres de los campos de la tabla tal cual (el índice los lee por nombre).
- En **Obligatoria para**, separa varias maestrías con `;` (los nombres de maestría pueden llevar comas).
- En **Horas fuera de clase / semana**, pon solo el número o rango (`3`, `4 – 6`); las aclaraciones van en una fila **Nota de carga**.
- Después de cambiar fichas, corre la evaluación (ver CONFIGURACION.md).

---

## 💰 Costo estimado

| Concepto | Costo |
|---|---|
| Hosting (Streamlit Community Cloud) | **$0 / mes** |
| API Gemini — tier gratuito | **$0** (con límites de uso diarios) |
| API Gemini — tier de pago | Por millón de tokens de entrada / salida / caché |
| **Total para uso piloto** | **$0** dentro del tier gratuito |

Los precios y límites cambian: consulta los vigentes en [ai.google.dev/pricing](https://ai.google.dev/pricing). El contador de tokens de la app muestra cuánto consume cada pregunta.

Con el caché de contexto, cada consulta lee la base (~55k tokens) a ~10% del precio normal de entrada. Ver la nota de costos del caché en CONFIGURACION.md.

---

## 🛠️ Stack tecnológico

| Componente | Tecnología |
|---|---|
| Interfaz | Streamlit |
| LLM | Google Gemini 2.5 Flash |
| SDK | `google-genai` (SDK oficial actual) |
| Contexto | Base completa + índice general + caché de contexto de Gemini |
| Base de conocimiento | Archivos Markdown |
| Registro (opcional) | Google Sheets vía `gspread` |
| Hosting | Streamlit Community Cloud |

---

## 📄 Licencia

Uso interno — Universidad Anáhuac Puebla.

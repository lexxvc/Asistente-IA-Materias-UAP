# 🎓 Asistente IA — Materias UAP

> Simulador de Trayectoria Académica para alumnos de maestría de la Universidad Anáhuac Puebla.

Asistente conversacional basado en inteligencia artificial que orienta a los estudiantes en la **selección de materias** y construcción de su **trayectoria académica**, respondiendo únicamente con información del catálogo oficial de la universidad.

---

## ✨ Características

- 💬 **Chat conversacional** con memoria de sesión — entiende preguntas de seguimiento
- 🔍 **RAG ligero** — recupera solo los documentos relevantes por pregunta (TF-IDF, sin dependencias externas)
- 📚 **83 materias** organizadas en 14 áreas de conocimiento
- ⚡ **Sin vector DB** — funciona con Python puro, sin ChromaDB ni embeddings
- 🔒 **Respuestas acotadas** al catálogo oficial — nunca inventa información
- 🚀 **Deploy en un clic** vía Streamlit Community Cloud

---

## 🗂️ Estructura del proyecto

```
Asistente-IA-Materias-UAP/
├── app.py                          ← Aplicación Streamlit + lógica RAG
├── requirements.txt                ← Solo 2 dependencias
├── .gitignore
├── .streamlit/
│   └── secrets.toml                ← API key (NO subir a GitHub)
└── conocimiento/
    ├── README.md
    ├── CIENCIA_DE_DATOS_E_INTELIGENCIA_ARTIFICIAL/
    │   ├── Inteligencia_artificial.md
    │   ├── Machine_learning.md
    │   ├── Ciencia_de_datos.md
    │   └── ...
    ├── DIRECCIÓN_Y_LIDERAZGO/
    ├── ECONOMÍA_Y_FINANZAS/
    └── ...  (14 áreas en total)
```

---

## 🧠 Áreas de conocimiento

| Área | Materias |
|------|----------|
| Administración y Gestión Pública | 6 |
| Análisis e Inteligencia de Negocios | 5 |
| Ciencia de Datos e Inteligencia Artificial | 7 |
| Comunicación | 6 |
| Derecho Empresarial | 6 |
| Dirección y Liderazgo | 6 |
| Economía y Finanzas | 6 |
| Fundamentos y Hospitalidad en la Salud | 5 |
| Ingeniería y Operaciones | 6 |
| Innovación Tecnológica y Emprendimiento | 5 |
| Mercadotecnia | 7 |
| Planeación y Estrategia | 5 |
| Talento Humano y Organizacional | 6 |
| Toma de Decisiones | 7 |
| **Total** | **83** |

---

## ⚙️ Cómo funciona

```
Pregunta del usuario
        │
        ▼
Tokenización + TF-IDF (Python puro)
        │
        ▼
Top 8 documentos relevantes recuperados
        │
        ▼
System prompt + contexto → Gemini 2.5 Flash
        │
        ▼
Respuesta acotada al catálogo oficial
```

El RAG está implementado sin librerías externas — solo `re`, `math` y `collections` de la biblioteca estándar de Python. Esto elimina costos de infraestructura (sin Pinecone, sin ChromaDB, sin OpenAI Embeddings) y reduce el consumo de tokens de entrada aproximadamente **10x** respecto a mandar toda la base de conocimiento en cada petición.

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
streamlit>=1.35.0
google-generativeai>=0.8.0
```

Sin dependencias de ML, sin bases de datos vectoriales, sin Docker.

---

## 📁 Actualizar la base de conocimiento

Los documentos son archivos Markdown planos — uno por materia. Para agregar o editar materias:

1. Edita o crea el archivo `.md` correspondiente en `conocimiento/<ÁREA>/`
2. Haz commit y push a GitHub
3. Streamlit Community Cloud redeploya automáticamente

**Formato recomendado para cada MD:**

```markdown
# Nombre de la Materia

> **Área de conocimiento:** NOMBRE DEL ÁREA

## 📋 Información general
| Campo | Detalle |
|---|---|
| **Obligatoria** | ✅ Sí / ❌ No |
| **Modalidad** | Presencial / Híbrida / En línea |
| **Nivel técnico** | Básico / Intermedio / Avanzado |
...

## 📝 Descripción
...

## 🎯 Perfil recomendado
...
```

---

## 💰 Costo estimado

| Concepto | Costo |
|---|---|
| Hosting (Streamlit Community Cloud) | **$0 / mes** |
| API Gemini — primeras 1,500 peticiones/día | **$0 / día** |
| API Gemini — uso por encima del tier gratuito | ~$0.30 USD / millón de tokens |
| **Total para uso piloto** | **$0** |

El RAG ligero reduce el contexto de ~100,000 tokens a ~10,000 tokens por consulta, lo que mantiene el costo mínimo incluso con modelos más avanzados como Gemini 2.5 Pro.

---

## 🛠️ Stack tecnológico

| Componente | Tecnología |
|---|---|
| Interfaz | Streamlit |
| LLM | Google Gemini 2.5 Flash |
| Recuperación | TF-IDF (Python estándar) |
| Base de conocimiento | Archivos Markdown |
| Hosting | Streamlit Community Cloud |

---

## 📄 Licencia

Uso interno — Universidad Anáhuac Puebla.

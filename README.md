# Asistente-IA-Materias-UAP
Apoyo en Selección de Trayectoria Herramienta de orientación académica para alumnos de maestría de la Universidad Anáhuac Puebla. Basada en el catálogo oficial de materias, responde tus preguntas y te ayuda a construir una trayectoria académica alineada a tus metas profesionales.


# 🎓 Asistente IA — Materias UAP

> Simulador de Trayectoria Académica para alumnos de maestría de la **Universidad Anáhuac Puebla**.  
> Orientación personalizada en la selección de materias mediante inteligencia artificial.

---

## ¿Qué es esto?

Un asistente conversacional que ayuda a los alumnos de maestría a explorar el catálogo de materias disponibles y construir su trayectoria académica. El alumno describe su perfil, intereses y objetivos profesionales, y el asistente le recomienda materias justificando cada sugerencia con base en el catálogo oficial.

El sistema responde **únicamente con información del catálogo institucional** — no inventa datos, docentes, horarios ni requisitos.

---

## Demo

🔗 **[Acceder al simulador →](https://asistente-ia-materias-uap-ewgj6h2rmnedppwdnjhs7m.streamlit.app/)**  
_(link disponible una vez desplegado en Streamlit Community Cloud)_

---

## Características

- 💬 Chat conversacional en lenguaje natural
- 📚 Base de conocimiento de **83 materias** en **14 áreas de conocimiento**
- 🧠 Motor de lenguaje: **Gemini 2.5 Flash** (Google AI)
- ⚡ Base de conocimiento cacheada en memoria — se carga una sola vez al iniciar la app
- 🔒 Responde solo con información presente en el catálogo oficial
- 🖥️ Desplegable gratuitamente en Streamlit Community Cloud

---

## Áreas de conocimiento

| # | Área |
|---|------|
| 1 | Administración y Gestión Pública |
| 2 | Análisis e Inteligencia de Negocios |
| 3 | Ciencia de Datos e Inteligencia Artificial |
| 4 | Comunicación |
| 5 | Derecho Empresarial |
| 6 | Dirección y Liderazgo |
| 7 | Economía y Finanzas |
| 8 | Fundamentos y Hospitalidad en la Salud |
| 9 | Ingeniería y Operaciones |
| 10 | Innovación Tecnológica y Emprendimiento |
| 11 | Mercadotecnia |
| 12 | Planeación y Estrategia |
| 13 | Talento Humano y Organizacional |
| 14 | Toma de Decisiones |

---

## Arquitectura

```
┌─────────────────────────────────────────────┐
│              Usuario (navegador)             │
└──────────────────────┬──────────────────────┘
                       │ pregunta
┌──────────────────────▼──────────────────────┐
│           Streamlit — app.py                │
│                                             │
│  1. Carga los 83 MDs al iniciar (cacheado)  │
│  2. Arma el system prompt con todo el       │
│     catálogo como contexto                  │
│  3. Llama a Gemini 2.5 Flash API            │
│  4. Devuelve respuesta al chat              │
└──────────────────────┬──────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
┌─────────▼────────┐     ┌──────────▼──────────┐
│  conocimiento/   │     │   Gemini 2.5 Flash   │
│  83 archivos .md │     │   (Google AI API)    │
│  14 carpetas     │     └─────────────────────-┘
└──────────────────┘
```

Los 83 archivos `.md` se leen y concatenan una sola vez al arrancar la app gracias a `@st.cache_data`, y se pasan completos como contexto al modelo en cada consulta.

---

## Estructura del proyecto

```
Asistente-IA-Materias-UAP/
├── app.py                          ← Aplicación principal (Streamlit)
├── requirements.txt                ← Dependencias (solo 2)
├── .gitignore                      ← Excluye secrets y caché
├── .streamlit/
│   └── secrets.toml                ← API key (NO incluir en el repo)
└── conocimiento/
    ├── README.md
    ├── CIENCIA_DE_DATOS_E_INTELIGENCIA_ARTIFICIAL/
    │   ├── Machine_learning.md
    │   ├── Inteligencia_artificial.md
    │   └── ...
    ├── ECONOMIA_Y_FINANZAS/
    │   └── ...
    └── ... (14 áreas, 83 materias)
```

---

## Instalación local

### Requisitos

- Python 3.10+
- Cuenta de Google AI Studio (para la API key de Gemini — gratuita)

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/lexxvc/Asistente-IA-Materias-UAP.git
cd Asistente-IA-Materias-UAP

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar la API key
mkdir -p .streamlit
echo 'GEMINI_API_KEY = "tu_api_key_aqui"' > .streamlit/secrets.toml

# 4. Correr la app
streamlit run app.py
```

La app estará disponible en `http://localhost:8501`

---

## Obtener la API key de Gemini (gratis)

1. Ve a [aistudio.google.com](https://aistudio.google.com)
2. Inicia sesión con tu cuenta de Google
3. Clic en **Get API Key** → **Create API key**
4. Copia la key y pégala en `.streamlit/secrets.toml`

> El tier gratuito incluye **1,500 peticiones/día** — más que suficiente para uso académico.

---

## Deploy en Streamlit Community Cloud (gratis)

1. Haz fork o sube este repo a tu GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io) e inicia sesión
3. Clic en **New app** → selecciona el repo → archivo: `app.py`
4. En **Settings → Secrets**, agrega:
   ```toml
   GEMINI_API_KEY = "tu_api_key_aqui"
   ```
5. Clic en **Deploy** — listo en ~2 minutos

La URL generada puede pegarse directamente en el micrositio institucional.

---

## Actualizar la base de conocimiento

Cada materia es un archivo `.md` independiente dentro de su carpeta de área. Para actualizar:

1. Edita o agrega archivos `.md` en `conocimiento/`
2. Haz commit y push a GitHub
3. Streamlit Community Cloud redeploya automáticamente

**Formato recomendado para cada materia:**

```markdown
# Nombre de la materia

> **Área de conocimiento:** NOMBRE DEL ÁREA

## 📋 Información general
| Campo | Detalle |
|---|---|
| **Obligatoria** | Sí / No |
| **Modalidad** | Presencial / Híbrida / En línea |
| **Nivel técnico** | Básico / Intermedio / Avanzado |
...

## 📝 Descripción
...

## 🎯 Perfil recomendado
...
```

---

## Dependencias

```
streamlit>=1.35.0
google-generativeai>=0.8.0
```

Solo dos paquetes. Sin ChromaDB, sin embeddings, sin vector DB.

---

## Costo estimado

| Componente | Costo |
|---|---|
| Streamlit Community Cloud | $0 |
| Gemini API (hasta 1,500 req/día) | $0 |
| Gemini API (sobre el límite gratuito) | ~$0.003 USD / consulta |

Para un uso académico normal el costo operativo es **$0/mes**.

---

## Contribuir

1. Haz fork del repositorio
2. Crea una rama: `git checkout -b mejora/nombre-de-la-mejora`
3. Haz commit de tus cambios: `git commit -m 'Agrega mejora X'`
4. Push a la rama: `git push origin mejora/nombre-de-la-mejora`
5. Abre un Pull Request

---

## Licencia

Uso interno — Universidad Anáhuac Puebla.

---

<div align="center">
  Desarrollado para la <strong>Universidad Anáhuac Puebla</strong><br/>
  Simulador de Trayectoria Académica · Maestrías
</div>
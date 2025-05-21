# 🏫 Sistema de Gestión Escolar con análisis y predicción usando IA

[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Open Issues](https://img.shields.io/github/issues/tu-usuario/gestion-escolar-ia)](https://github.com/tu-usuario/gestion-escolar-ia/issues)

Aplicación web inteligente para la gestión académica y la predicción del rendimiento estudiantil mediante IA.

![Dashboard Preview](/image/dashboard.png)

# 📂 Estructura del Proyecto
```bash
gestion-escolar-ia/
├── 📂 image/              # Recursos visuales
│   ├── dashboard.png      # Captura del dashboard
├── 📂 data/               # Conjuntos de datos de ejemplo
│   ├── datos_escolares_ejemplo.csv    # Datos de ejemplo
├── 📜 gestion_escolar.py  # Código principal
├── 📜 requirements.txt    # Dependencias
└── 📜 README.md           # Información
```

## ✨ Características Principales

- 📊 Dashboard interactivo con métricas clave
- 🧠 Integración con modelos de IA (Claude, HuggingFace)
- 📈 Visualizaciones dinámicas con Plotly
- 🔍 Análisis personalizado por estudiante
- 🤖 Generación de feedback automatizado
- 📦 Soporte para datos de ejemplo o carga de archivos CSV

### 💻 Requisitos
- Python 3.8+
- Cuenta en [Anthropic](https://www.anthropic.com/) (opcional para Claude AI)
- Cuenta en [HuggingFace](https://huggingface.co/) (opcional)

1. Crear entorno virtual (recomendado)
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

# 📄 Uso Básico
- Iniciar la aplicación
- Cargar datos (ejemplo o archivo CSV)
- Explorar las pestañas del dashboard:
  - 📊 Resumen general
  - 📈 Análisis por estudiante
  - 🧠 Recomendaciones IA
- Exportar resultados en CSV

## 📌 Instalar dependencias e iniciar
```bash
git clone https://github.com/tu-usuario/gestion-escolar-ia.git
cd gestion-escolar-ia
pip install -r requirements.txt
```

## 🚀 Despliegue Rápido
```bash
streamlit run gestion_escolar.py
```
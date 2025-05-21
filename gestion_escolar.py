import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.cluster import KMeans
from transformers import pipeline
import requests
from io import StringIO
import os

# Configuración
st.set_page_config(page_title="Gestión Escolar IA", layout="wide", page_icon="🏫")
st.title("🏫 Plataforma de Gestión Escolar con Análisis Predictivo")

# Configuración de APIs
with st.sidebar:
    st.header("🔑 Configuración de API Keys")
    ANTHROPIC_API_KEY = st.text_input("Ingresa tu API Key de Anthropic (Claude)", type="password")
    HF_API_KEY = st.text_input("Ingresa tu API Key de HuggingFace (opcional)", type="password")

    st.divider()
    st.header("⚙️ Configuración")
    nota_minima = st.slider("Nota mínima para aprobar", 0, 20, 11)
    asistencia_minima = st.slider("Asistencia mínima (%)", 0, 100, 80)

    st.divider()
    st.header("🔧 Configuración IA")
    use_ai_feedback = st.toggle("Usar IA para feedback", True)
    use_clustering = st.toggle("Agrupamiento con IA", True)
    ai_preference = st.selectbox("Preferencia de IA", ["Claude (API)", "HuggingFace (Local)", "HuggingFace (API)"])

# Modelos disponibles
HF_MODELS = {
    "GPT2 (Pequeño)": "gpt2",
    "DistilGPT2 (Rápido)": "distilgpt2",
    "Bloom (560M)": "bigscience/bloom-560m"
}

# --- Datos de Ejemplo ---
def crear_datos_ejemplo():
    data = {
        "Nombre": ["Juan Pérez", "María López", "Carlos Quispe", "Ana Mendoza", "Luis García"],
        "Bim1": [14, 16, 11, 18, 8],
        "Bim2": [15, 17, 12, 17, 9],
        "Bim3": [13, 18, 10, 19, 10],
        "Bim4": [16, 17, 13, 18, 12],
        "Asistencia": [95, 98, 85, 97, 70],
        "Conducta": ["Bueno", "Excelente", "Regular", "Excelente", "Bajo"]
    }
    return pd.DataFrame(data)

# --- Funciones de IA ---
def generate_with_claude(prompt, api_key):
    """Genera texto usando la API de Claude"""
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        else:
            st.error(f"Error en API Claude: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        st.error(f"Excepción al usar Claude: {str(e)}")
        return None

def generate_with_hf_local(prompt, model_name):
    """Genera texto con modelos locales de HuggingFace"""
    try:
        generator = pipeline('text-generation', model=model_name)
        result = generator(prompt, max_length=500, do_sample=True, temperature=0.7)
        return result[0]['generated_text']
    except Exception as e:
        st.error(f"Error con modelo local: {str(e)}")
        return None

def generate_with_hf_api(prompt, model_name, api_key):
    """Genera texto con la API de HuggingFace"""
    try:
        API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})

        if response.status_code == 200:
            return response.json()[0]['generated_text']
        else:
            st.error(f"Error en API HuggingFace: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Excepción al usar HuggingFace API: {str(e)}")
        return None

# --- Función para análisis básico ---
def show_basic_analysis(student_data):
    """Muestra un análisis básico cuando fallan los modelos de IA"""
    st.subheader("Análisis Básico")

    # Evaluación de notas
    if student_data['Nota_Final'] < nota_minima:
        st.error(f"⚠️ Nota final ({student_data['Nota_Final']}) está por debajo del mínimo requerido ({nota_minima})")
    else:
        st.success(f"✅ Nota final ({student_data['Nota_Final']}) cumple con el mínimo requerido")

    # Evaluación de asistencia
    if student_data['Asistencia'] < asistencia_minima:
        st.error(f"⏰ Asistencia ({student_data['Asistencia']}%) está por debajo del mínimo requerido ({asistencia_minima}%)")
    else:
        st.success(f"📅 Asistencia ({student_data['Asistencia']}%) cumple con el mínimo requerido")

    # Recomendaciones generales
    st.write("**Recomendaciones:**")
    if student_data['Nota_Final'] < nota_minima:
        st.write("- Reforzar temas con menores calificaciones")
    if student_data['Asistencia'] < asistencia_minima:
        st.write("- Mejorar la asistencia a clases")
    st.write("- Consultar con el tutor si persisten dificultades")

# --- Cargar Datos ---
df = None
if st.checkbox("📁 Usar datos de ejemplo"):
    df = crear_datos_ejemplo()
else:
    uploaded_file = st.file_uploader("Sube tu CSV (Columnas: Nombre, Bim1-4, Asistencia, Conducta)")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)

# --- Procesamiento ---
if df is not None:
    # Convertir columnas numéricas
    numeric_cols = ['Bim1', 'Bim2', 'Bim3', 'Bim4', 'Asistencia']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Cálculos
    df["Nota_Final"] = df[["Bim1", "Bim2", "Bim3", "Bim4"]].mean(axis=1).round(1)
    df["Aprobado"] = np.where((df["Nota_Final"] >= nota_minima) &
                            (df["Asistencia"] >= asistencia_minima), "✅ Sí", "❌ No")

    # --- Dashboard ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumen", "📈 Análisis", "🧠 IA Avanzada", "📄 Datos"])

    with tab1:
        st.header("Métricas Clave")
        cols = st.columns(4)
        cols[0].metric("Total Estudiantes", len(df))
        cols[1].metric("Aprobación", f"{len(df[df['Aprobado'] == '✅ Sí'])/len(df)*100:.1f}%")
        cols[2].metric("Asistencia Prom.", f"{df['Asistencia'].mean():.1f}%")
        cols[3].metric("Nota Promedio", f"{df['Nota_Final'].mean():.1f}")

        st.divider()
        st.header("Evolución Bimestral")
        fig = px.line(df[numeric_cols].mean().reset_index(),
                     x='index', y=0, markers=True,
                     labels={'index':'Bimestre', '0':'Nota Promedio'},
                     title="Rendimiento por Bimestre")
        fig.add_hline(y=nota_minima, line_dash="dot", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.header("Análisis Detallado")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Distribución de Notas Finales")
            fig = px.histogram(df, x="Nota_Final", nbins=10,
                              color_discrete_sequence=['#636EFA'])
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Rendimiento vs Asistencia")
            fig = px.scatter(df, x="Asistencia", y="Nota_Final",
                           color="Aprobado", hover_name="Nombre",
                           color_discrete_map={"✅ Sí": "green", "❌ No": "red"})
            st.plotly_chart(fig, use_container_width=True)

        if 'Conducta' in df.columns:
            st.subheader("Comparación por Conducta")
            fig = px.box(df, x="Conducta", y="Nota_Final", color="Conducta")
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.header("Herramientas IA")

        if use_clustering and all(col in df.columns for col in ['Nota_Final', 'Asistencia']):
            st.subheader("Agrupamiento de Estudiantes")
            try:
                X = df[['Nota_Final', 'Asistencia']]
                kmeans = KMeans(n_clusters=3, random_state=42).fit(X)
                df['Grupo_IA'] = kmeans.labels_

                fig = px.scatter(df, x="Asistencia", y="Nota_Final",
                               color="Grupo_IA", hover_name="Nombre",
                               title="Agrupamiento por Rendimiento y Asistencia")
                st.plotly_chart(fig, use_container_width=True)

                for i in range(3):
                    group_data = df[df['Grupo_IA'] == i]
                    st.write(f"👥 Grupo {i+1}: {len(group_data)} estudiantes | " +
                            f"Nota: {group_data['Nota_Final'].mean():.1f} | " +
                            f"Asistencia: {group_data['Asistencia'].mean():.1f}%")
            except Exception as e:
                st.error(f"Error en clustering: {str(e)}")

        if use_ai_feedback:
            st.subheader("Feedback Personalizado con IA")
            student = st.selectbox("Selecciona estudiante", df['Nombre'])
            selected_model = st.selectbox("Selecciona modelo de respaldo", list(HF_MODELS.keys()))

            if st.button("Generar Análisis"):
                try:
                    student_data = df[df['Nombre'] == student].iloc[0]
                    prompt = f"""
                    Eres un profesor y/o tutor de una institución educativa. Analiza el rendimiento escolar de {student}:

                    Datos académicos:
                    - Notas por bimestre: {student_data['Bim1']}, {student_data['Bim2']}, {student_data['Bim3']}, {student_data['Bim4']}
                    - Nota final: {student_data['Nota_Final']} (mínimo aprobatorio: {nota_minima})
                    - Asistencia: {student_data['Asistencia']}% (mínimo requerido: {asistencia_minima}%)
                    - Conducta: {student_data.get('Conducta', 'No especificada')}

                    Proporciona un análisis educativo con:
                    1. Evaluación del desempeño general
                    2. Fortalezas y áreas de oportunidad
                    3. Recomendaciones específicas para mejorar
                    4. Estrategias personalizadas según el perfil del estudiante

                    Usa un tono profesional pero cercano, adecuado para docentes y padres de familia.
                    """

                    analysis = None

                    # Intento con Claude primero si está configurado como preferencia
                    if ai_preference == "Claude (API)" and ANTHROPIC_API_KEY:
                        analysis = generate_with_claude(prompt, ANTHROPIC_API_KEY)

                    # Fallback según preferencia
                    if analysis is None:
                        if ai_preference == "HuggingFace (Local)":
                            analysis = generate_with_hf_local(prompt, HF_MODELS[selected_model])
                        elif ai_preference == "HuggingFace (API)" and HF_API_KEY:
                            analysis = generate_with_hf_api(prompt, HF_MODELS[selected_model], HF_API_KEY)

                    # Mostrar resultados
                    if analysis:
                        st.markdown("### Análisis generado por IA:")
                        st.write(analysis)
                    else:
                        st.warning("No se pudo generar el análisis con IA. Mostrando análisis básico...")
                        show_basic_analysis(student_data)

                except Exception as e:
                    st.error(f"Error general: {str(e)}")
                    show_basic_analysis(student_data)

    with tab4:
        st.header("Datos Completos")
        st.dataframe(df.style.apply(
            lambda x: ['background: #ffcccc'
                      if isinstance(v, (int, float)) and v < nota_minima and k.startswith('Bim')
                      else ''
                      for k, v in x.items()],
            axis=1
        ))

        # Exportar datos
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "datos_escolares.csv", "text/csv")

else:
    st.warning("Por favor carga tus datos o activa los datos de ejemplo")

# --- Footer ---
st.divider()
st.caption("Sistema de Gestión Escolar con IA | © 2025")
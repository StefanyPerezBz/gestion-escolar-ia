import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import datetime
from fpdf import FPDF
from io import BytesIO

# Configuración de la página
st.set_page_config(
    page_title="Sistema Escolar con IA",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados (compatible con modo oscuro)
st.markdown("""
<style>
    .header {
        font-size: 2.2em;
        color: #1f3c73;
        border-bottom: 3px solid #D91023;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .dark .header {
        color: #4a90e2;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .dark .metric-card {
        background-color: #2d3748;
    }
    .info-box {
        background-color: #e3f2fd;
        border-left: 5px solid #2196F3;
        padding: 15px;
        margin: 15px 0;
        border-radius: 5px;
    }
    .dark .info-box {
        background-color: #2a4365;
        border-left: 5px solid #63b3ed;
    }
    .error-box {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 15px;
        margin: 15px 0;
        border-radius: 5px;
    }
    .dark .error-box {
        background-color: #742a2a;
        border-left: 5px solid #f56565;
    }
    .success-box {
        background-color: #e8f5e9;
        border-left: 5px solid #4CAF50;
        padding: 15px;
        margin: 15px 0;
        border-radius: 5px;
    }
    .dark .success-box {
        background-color: #22543d;
        border-left: 5px solid #48bb78;
    }
    .stTabs [aria-selected="true"] {
        font-weight: bold;
        color: #1f3c73 !important;
    }
    .dark .stTabs [aria-selected="true"] {
        color: #4a90e2 !important;
    }
    .legend {
        background-color: #f5f5f5;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .dark .legend {
        background-color: #2d3748;
    }
    .guide-box {
        background-color: #fff3e0;
        border-left: 5px solid #FFA000;
        padding: 15px;
        margin: 15px 0;
        border-radius: 5px;
    }
    .dark .guide-box {
        background-color: #5a3921;
        border-left: 5px solid #f6ad55;
    }
    .data-guide {
        font-family: monospace;
        background-color: #f5f5f5;
        padding: 10px;
        border-radius: 5px;
        overflow-x: auto;
    }
    .dark .data-guide {
        background-color: #1a202c;
    }
</style>
""", unsafe_allow_html=True)

# --- Cabecera ---
st.markdown('<div class="header">📊 Sistema de Gestión Escolar con IA</div>', unsafe_allow_html=True)
st.caption("Herramienta para el seguimiento académico según normas del Ministerio de Educación del Perú")

# --- Variables de sesión ---
if 'df' not in st.session_state:
    st.session_state.df = None
if 'nivel_educativo' not in st.session_state:
    st.session_state.nivel_educativo = None

# --- Configuración del sidebar ---
with st.sidebar:
    st.header("🔐 Configuración API Claude")
    ANTHROPIC_API_KEY = st.text_input(
        "Ingrese su API Key de Anthropic",
        type="password",
        help="Opcional para análisis con IA"
    )

    st.markdown("---")
    st.header("⚙️ Parámetros Académicos")

    # Detectar nivel educativo automáticamente si hay datos cargados
    if st.session_state.df is not None and 'Grado' in st.session_state.df.columns:
        grados_unicos = st.session_state.df['Grado'].unique()
        if any('Primaria' in str(grado) for grado in grados_unicos):
            st.session_state.nivel_educativo = 'Primaria'
        elif any('Secundaria' in str(grado) for grado in grados_unicos):
            st.session_state.nivel_educativo = 'Secundaria'
        else:
            st.session_state.nivel_educativo = 'Ambos'

    # Selector de nivel educativo
    nivel_options = []
    if st.session_state.nivel_educativo is None:
        nivel_options = ['Primaria', 'Secundaria', 'Ambos']
    else:
        nivel_options = [st.session_state.nivel_educativo] if st.session_state.nivel_educativo != 'Ambos' else ['Ambos']

    nivel_educativo = st.selectbox(
        "Nivel Educativo",
        nivel_options if nivel_options else ['Primaria', 'Secundaria', 'Ambos'],
        disabled=len(nivel_options) == 1
    )

    # Configuración específica por nivel
    if nivel_educativo in ["Primaria", "Ambos"]:
        nota_minima_prim = st.slider(
            "Nota mínima aprobatoria (Primaria)",
            min_value=0,
            max_value=20,
            value=11,
            help="Según normativa MINEDU para Primaria (escala 0-20)"
        )
        usar_letras_prim = True  # Siempre usar letras en Primaria

    if nivel_educativo in ["Secundaria", "Ambos"]:
        nota_minima_sec = st.slider(
            "Nota mínima aprobatoria (Secundaria)",
            min_value=0,
            max_value=10,
            value=10,
            help="Según normativa MINEDU para Secundaria (escala 0-10)"
        )
        usar_letras_sec = st.checkbox(
            "Usar sistema de letras en Secundaria",
            value=False,
            help="Misma escala que Primaria: C (0-10), B (11-13), A (14-17), AD (18-20)"
        )

    st.markdown("---")
    st.header("📅 Asistencia Escolar")
    asistencia_minima = st.slider(
        "Asistencia mínima requerida (%)",
        min_value=60,
        max_value=100,
        value=80
    )

    # Guía para calcular asistencia
    with st.expander("ℹ️ ¿Cómo calcular el porcentaje de asistencia?"):
        st.markdown("""
        **Fórmula para calcular el porcentaje de asistencia:**

        ```
        Porcentaje de Asistencia = (Días asistidos / Total días de clases) × 100
        ```

        **Ejemplo:**
        Si el año escolar tiene 200 días de clases y el estudiante asistió 180 días:

        ```
        (180 / 200) × 100 = 90%
        ```

        **Recomendaciones:**
        - Considere días justificados (enfermedad con certificado médico)
        - No cuente como inasistencia los feriados o días no laborables
        - Registre la asistencia bimestralmente para mayor precisión
        """)

    st.markdown("---")
    st.header("📅 Periodo Académico")
    hoy = datetime.date.today()
    if hoy.month < 7:
        periodo = f"Primer Semestre {hoy.year} (Enero-Julio)"
    else:
        periodo = f"Segundo Semestre {hoy.year} (Agosto-Diciembre)"
    st.write(periodo)

# --- Sistema de Letras Ajustado ---
def convertir_a_letras(nota, nivel):
    """Convierte nota numérica a letras según escala MINEDU"""
    # Mismo sistema para Primaria y Secundaria cuando está activado
    if nivel == "Secundaria" and not usar_letras_sec:
        return "-"

    if nota <= 10: return "C"
    elif 11 <= nota <= 13: return "B"
    elif 14 <= nota <= 17: return "A"
    elif nota >= 18: return "AD"
    else: return "-"

# --- Datos de ejemplo ---
@st.cache_data
def generar_datos_ejemplo(nivel):
    if nivel in ["Primaria", "Ambos"]:
        grados_prim = [f"{i}° Primaria" for i in range(1, 7)]
        estudiantes_prim = [
            "Juan Pérez Quispe", "María López García",
            "Carlos Rojas Flores", "Ana Díaz Mendoza",
            "Luis Torres Vásquez", "Sofía Castro Ruiz"
        ]

    if nivel in ["Secundaria", "Ambos"]:
        grados_sec = [f"{i}° Secundaria" for i in range(1, 6)]
        estudiantes_sec = [
            "Miguel Ángel Soto", "Lucía Fernández Ramos",
            "Diego Mendoza Cruz", "Valeria Gómez Huamán",
            "Jorge Paredes Salas"
        ]

    if nivel == "Primaria":
        estudiantes = estudiantes_prim
        grados = grados_prim
    elif nivel == "Secundaria":
        estudiantes = estudiantes_sec
        grados = grados_sec
    else:  # Ambos
        estudiantes = estudiantes_prim + estudiantes_sec
        grados = grados_prim + grados_sec

    datos = {
        "Estudiante": estudiantes,
        "DNI": [str(80000000 + i) for i in range(len(estudiantes))],
        "Grado": np.random.choice(grados, len(estudiantes)),
        "Bim1": np.random.randint(5, 20, len(estudiantes)),
        "Bim2": np.random.randint(5, 20, len(estudiantes)),
        "Bim3": np.random.randint(5, 20, len(estudiantes)),
        "Bim4": np.random.randint(5, 20, len(estudiantes)),
        "Asistencia": np.random.randint(70, 100, len(estudiantes)),
        "Conducta": np.random.choice(["Excelente", "Bueno", "Regular"], len(estudiantes))
    }
    return pd.DataFrame(datos)

# --- Guía para formato de datos ---
def mostrar_guia_formato():
    st.markdown("""
    <div class="guide-box">
        <h4>📋 Guía para preparar sus datos</h4>
        <p>Para que el sistema funcione correctamente, su archivo debe contener las siguientes columnas:</p>

        <div class="data-guide">
        Estudiante, DNI, Grado, Bim1, Bim2, Bim3, Bim4, Asistencia [, Conducta]
        </div>

        <p><strong>Requisitos:</strong></p>
        <ul>
            <li><strong>Estudiante:</strong> Nombre completo del estudiante</li>
            <li><strong>DNI:</strong> Documento de identidad (8 dígitos)</li>
            <li><strong>Grado:</strong> Ejemplo: "1° Primaria", "3° Secundaria"</li>
            <li><strong>Bim1-Bim4:</strong> Notas de cada bimestre (números enteros o decimales)</li>
            <li><strong>Asistencia:</strong> Porcentaje de asistencia (0-100)</li>
            <li><strong>Conducta (opcional):</strong> Evaluación cualitativa</li>
        </ul>

        <p><strong>Ejemplo de datos válidos:</strong></p>
        <div class="data-guide">
        Estudiante,DNI,Grado,Bim1,Bim2,Bim3,Bim4,Asistencia,Conducta<br>
        Juan Pérez Quispe,87654321,2° Primaria,14,15,13,16,95,Excelente<br>
        María López García,12345678,4° Secundaria,12,11,13,10,85,Bueno<br>
        Carlos Rojas Flores,23456789,1° Primaria,16,17,15,18,100,Excelente
        </div>

        <p>Puede descargar una <a href="#" id="plantilla-link">plantilla en formato CSV</a> para referencia.</p>
    </div>
    """, unsafe_allow_html=True)

    # Script para descargar plantilla
    st.markdown("""
    <script>
    document.getElementById('plantilla-link').addEventListener('click', function() {
        var csv = 'Estudiante,DNI,Grado,Bim1,Bim2,Bim3,Bim4,Asistencia,Conducta\\n' +
                  'Juan Pérez Quispe,87654321,2° Primaria,14,15,13,16,95,Excelente\\n' +
                  'María López García,12345678,4° Secundaria,12,11,13,10,85,Bueno\\n' +
                  'Carlos Rojas Flores,23456789,1° Primaria,16,17,15,18,100,Excelente';

        var blob = new Blob([csv], { type: 'text/csv' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.setAttribute('hidden', '');
        a.setAttribute('href', url);
        a.setAttribute('download', 'plantilla_datos_escolares.csv');
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    });
    </script>
    """, unsafe_allow_html=True)

# --- Carga de datos ---
df = None
modo = st.radio(
    "Seleccione el modo de operación:",
    ["Usar datos de ejemplo", "Subir archivo propio"],
    horizontal=True
)

if modo == "Subir archivo propio":
    mostrar_guia_formato()

if modo == "Usar datos de ejemplo":
    df = generar_datos_ejemplo(nivel_educativo)
    st.session_state.df = df
    st.session_state.nivel_educativo = nivel_educativo

    st.markdown(f"""
    <div class="info-box">
        <h4>🔍 MODO DEMOSTRACIÓN - {nivel_educativo}</h4>
        <p>Está viendo datos simulados de {nivel_educativo.lower()}. Para analizar sus propios datos, seleccione "Subir archivo propio".</p>
    </div>
    """, unsafe_allow_html=True)
else:
    uploaded_file = st.file_uploader(
        "Suba su archivo Excel o CSV",
        type=["xlsx", "csv"],
        help="El archivo debe contener columnas para Estudiante, DNI, Grado, Bim1-Bim4 y Asistencia"
    )

    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file, engine='openpyxl')

            # Validación de columnas
            required_cols = ["Estudiante", "DNI", "Grado", "Bim1", "Bim2", "Bim3", "Bim4", "Asistencia"]
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                st.markdown(f"""
                <div class="error-box">
                    <h4>❌ Error en el formato del archivo</h4>
                    <p>Faltan las siguientes columnas requeridas: <strong>{", ".join(missing_cols)}</strong></p>
                    <p>Revise la guía de formato arriba para asegurarse que su archivo tiene la estructura correcta.</p>
                </div>
                """, unsafe_allow_html=True)
                st.stop()

            # Validación de datos
            for bim in ["Bim1", "Bim2", "Bim3", "Bim4"]:
                df[bim] = pd.to_numeric(df[bim], errors='coerce')
                if df[bim].isnull().any():
                    st.error(f"❌ Las notas en {bim} contienen valores no numéricos")
                    st.stop()
                df[bim] = df[bim].clip(0, 20)

            df["Asistencia"] = pd.to_numeric(df["Asistencia"], errors='coerce').clip(0, 100)

            st.session_state.df = df
            st.session_state.nivel_educativo = nivel_educativo

            st.markdown(f"""
            <div class="success-box">
                <h4>✅ Archivo cargado correctamente</h4>
                <p>Se procesaron {len(df)} registros de estudiantes.</p>
            </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.markdown(f"""
            <div class="error-box">
                <h4>❌ Error al procesar el archivo</h4>
                <p>Ocurrió un problema al leer el archivo. Verifique que:</p>
                <ul>
                    <li>El archivo no esté corrupto</li>
                    <li>Tenga el formato correcto (CSV o Excel)</li>
                    <li>No contenga caracteres especiales problemáticos</li>
                </ul>
                <p><strong>Detalle técnico:</strong> {str(e)}</p>
            </div>
            """, unsafe_allow_html=True)
            st.stop()

# --- Procesamiento de datos ---
if st.session_state.df is not None:
    df = st.session_state.df.copy()

    # Determinar parámetros según nivel educativo
    def get_params(row):
        if "Primaria" in str(row["Grado"]):
            return nota_minima_prim, usar_letras_prim
        elif "Secundaria" in str(row["Grado"]):
            return nota_minima_sec, usar_letras_sec
        else:
            return (nota_minima_prim, usar_letras_prim) if nivel_educativo == "Primaria" else (nota_minima_sec, usar_letras_sec)

    # Calcular promedio y estado
    df["Promedio"] = df[["Bim1", "Bim2", "Bim3", "Bim4"]].mean(axis=1).round(1)

    # Aplicar criterios por nivel educativo
    df["Nota_Minima"] = df.apply(
        lambda row: nota_minima_prim if "Primaria" in str(row["Grado"]) else nota_minima_sec,
        axis=1
    )

    df["Estado"] = np.where(
        (df["Promedio"] >= df["Nota_Minima"]) & (df["Asistencia"] >= asistencia_minima),
        "Aprobado", "Desaprobado"
    )

    # Aplicar sistema de letras según nivel
    df["Letra"] = df.apply(
        lambda row: convertir_a_letras(row["Promedio"], "Primaria" if "Primaria" in str(row["Grado"]) else "Secundaria"),
        axis=1
    )

    # --- Dashboard Principal ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Resumen General",
        "📈 Análisis Comparativo",
        "🧑‍🎓 Análisis Individual",
        "📝 Reportes"
    ])

    with tab1:
        st.markdown("### 📌 Resumen Académico")

        # Métricas clave
        cols = st.columns(4)
        with cols[0]:
           st.markdown(f"""
    <div class="metric-card">
        <h4>Total Estudiantes</h4>
        <h2>{len(df)}</h2>
        <p style="font-size: 0.8em; color: #666;">
            {len(df[df['Grado'].str.contains('Primaria')])} Primaria<br>
            {len(df[df['Grado'].str.contains('Secundaria')])} Secundaria
        </p>
    </div>
    """, unsafe_allow_html=True)

        with cols[1]:
            st.markdown(f"""
            <div class="metric-card">
                <h4>% Aprobación</h4>
                <h2>{len(df[df['Estado'] == 'Aprobado']) / len(df) * 100:.1f}%</h2>
                <p style="font-size: 0.8em; color: #666;">{len(df[df['Estado'] == 'Aprobado'])} aprobados</p>
            </div>
            """, unsafe_allow_html=True)

        with cols[2]:
            st.markdown(f"""
            <div class="metric-card">
                <h4>Nota Promedio</h4>
                <h2>{df['Promedio'].mean():.1f}</h2>
                <p style="font-size: 0.8em; color: #666;">Rango: {df['Promedio'].min():.1f}-{df['Promedio'].max():.1f}</p>
            </div>
            """, unsafe_allow_html=True)

        with cols[3]:
            st.markdown(f"""
            <div class="metric-card">
                <h4>Asistencia Prom.</h4>
                <h2>{df['Asistencia'].mean():.1f}%</h2>
                <p style="font-size: 0.8em; color: #666;">Mínimo requerido: {asistencia_minima}%</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Gráfico 1: Distribución de notas
        st.markdown("#### 📉 Distribución de Notas Finales")
        fig1 = px.histogram(
            df,
            x="Promedio",
            nbins=20,
            color_discrete_sequence=["#1f3c73"],
            labels={"Promedio": "Nota Promedio (0-20)"},
            hover_data=["Estudiante", "Grado"],
            facet_col="Grado" if nivel_educativo == "Ambos" else None
        )

        # Añadir líneas de aprobación según nivel
        if nivel_educativo == "Ambos":
            fig1.add_hline(y=nota_minima_prim, line_dash="dash", line_color="red", row=1, col=1)
            fig1.add_hline(y=nota_minima_sec, line_dash="dash", line_color="red", row=1, col=2)
        else:
            nota_min = nota_minima_prim if nivel_educativo == "Primaria" else nota_minima_sec
            fig1.add_vline(x=nota_min, line_dash="dash", line_color="red")

        fig1.update_layout(bargap=0.1)
        st.plotly_chart(fig1, use_container_width=True)

        # Leyenda del gráfico
        st.markdown("""
        <div class="legend">
            <h4>📌 Interpretación del gráfico:</h4>
            <ul>
                <li>El histograma muestra cuántos estudiantes hay en cada rango de notas</li>
                <li>La <span style="color:red;font-weight:bold;">línea roja</span> indica la nota mínima requerida para aprobar</li>
                <li>Las barras a la izquierda de la línea representan estudiantes en riesgo</li>
                <li>Un patrón ideal muestra mayoría de estudiantes a la derecha de la línea</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # Gráfico 2: Rendimiento por grado
        st.markdown("#### 🎓 Rendimiento por Grado")
        fig2 = px.box(
            df,
            x="Grado",
            y="Promedio",
            color="Grado",
            points="all",
            hover_name="Estudiante",
            labels={"Promedio": "Nota Promedio"},
            height=500
        )

        # Añadir líneas de aprobación según nivel
        if nivel_educativo == "Ambos":
            for i, grado in enumerate(df["Grado"].unique()):
                if "Primaria" in grado:
                    fig2.add_hline(y=nota_minima_prim, line_dash="dash", line_color="red", row=1, col=i+1)
                else:
                    fig2.add_hline(y=nota_minima_sec, line_dash="dash", line_color="red", row=1, col=i+1)
        else:
            nota_min = nota_minima_prim if nivel_educativo == "Primaria" else nota_minima_sec
            fig2.add_hline(y=nota_min, line_dash="dash", line_color="red")

        st.plotly_chart(fig2, use_container_width=True)

        # Leyenda del gráfico
        st.markdown("""
        <div class="legend">
            <h4>📌 Cómo leer este gráfico:</h4>
            <ul>
                <li><strong>Caja:</strong> Representa el 50% central de los datos (entre el percentil 25 y 75)</li>
                <li><strong>Línea en la caja:</strong> Es la mediana (el valor que divide los datos en dos partes iguales)</li>
                <li><strong>Bigotes:</strong> Muestran el rango normal de los datos (excluyendo valores atípicos)</li>
                <li><strong>Puntos:</strong> Representan estudiantes con rendimiento atípico (fuera del rango normal)</li>
                <li>Entre más alta esté la caja, mejor el rendimiento del grupo</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # Nuevo Gráfico 3: Asistencia vs Rendimiento
        st.markdown("#### 📅 Relación Asistencia vs Rendimiento")
        fig3 = px.scatter(
            df,
            x="Asistencia",
            y="Promedio",
            color="Estado",
            color_discrete_map={"Aprobado": "#4CAF50", "Desaprobado": "#F44336"},
            hover_name="Estudiante",
            size_max=15,
            labels={"Promedio": "Nota Promedio", "Asistencia": "Asistencia (%)"},
            facet_col="Grado" if nivel_educativo == "Ambos" else None
        )

        # Añadir líneas de corte
        if nivel_educativo == "Ambos":
            for i, grado in enumerate(df["Grado"].unique()):
                if "Primaria" in grado:
                    fig3.add_hline(y=nota_minima_prim, line_dash="dash", line_color="red", row=1, col=i+1)
                else:
                    fig3.add_hline(y=nota_minima_sec, line_dash="dash", line_color="red", row=1, col=i+1)
        else:
            nota_min = nota_minima_prim if nivel_educativo == "Primaria" else nota_minima_sec
            fig3.add_hline(y=nota_min, line_dash="dash", line_color="red")

        fig3.add_vline(x=asistencia_minima, line_dash="dash", line_color="red")
        st.plotly_chart(fig3, use_container_width=True)

        # Leyenda del gráfico
        st.markdown("""
        <div class="legend">
            <h4>📌 Zonas de interpretación:</h4>
            <ul>
                <li><span style="color:#4CAF50;font-weight:bold;">Verde:</span> Estudiantes aprobados (cumplen ambos requisitos)</li>
                <li><span style="color:#F44336;font-weight:bold;">Rojo:</span> Estudiantes desaprobados (falta en notas, asistencia o ambos)</li>
                <li><strong>Cuadrante superior izquierdo:</strong> Buen rendimiento pero baja asistencia (riesgo por inasistencia)</li>
                <li><strong>Cuadrante inferior derecho:</strong> Buena asistencia pero bajo rendimiento (necesitan refuerzo académico)</li>
                <li><strong>Cuadrante inferior izquierdo:</strong> Riesgo alto (intervención urgente necesaria)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.markdown("### 📊 Análisis Comparativo")

        # Gráfico 4: Evolución bimestral promedio
        st.markdown("#### 📅 Evolución Bimestral (Promedio)")

        if nivel_educativo == "Ambos":
            fig4 = px.line(
                df.groupby("Grado")[["Bim1", "Bim2", "Bim3", "Bim4"]].mean().T.reset_index(),
                x="index",
                y=df["Grado"].unique(),
                labels={"index": "Bimestre", "value": "Nota Promedio"},
                title="Evolución por Grado",
                markers=True
            )

            # Añadir líneas de aprobación
            for i, grado in enumerate(df["Grado"].unique()):
                if "Primaria" in grado:
                    fig4.add_hline(y=nota_minima_prim, line_dash="dash", line_color="red", row=1, col=1)
                else:
                    fig4.add_hline(y=nota_minima_sec, line_dash="dash", line_color="red", row=1, col=1)
        else:
            bimestres_prom = df[["Bim1", "Bim2", "Bim3", "Bim4"]].mean().reset_index()
            bimestres_prom.columns = ["Bimestre", "Nota"]

            fig4 = px.line(
                bimestres_prom,
                x="Bimestre",
                y="Nota",
                markers=True,
                text="Nota",
                labels={"Nota": "Nota Promedio"},
                range_y=[0, 20]
            )

            nota_min = nota_minima_prim if nivel_educativo == "Primaria" else nota_minima_sec
            fig4.add_hline(y=nota_min, line_dash="dash", line_color="red")

        fig4.update_traces(
            textposition="top center",
            line=dict(width=3),
            marker=dict(size=10)
        )
        st.plotly_chart(fig4, use_container_width=True)

        # Leyenda del gráfico
        st.markdown("""
        <div class="legend">
            <h4>📌 Tendencias a observar:</h4>
            <ul>
                <li><strong>Línea ascendente:</strong> Mejora continua en el aprendizaje</li>
                <li><strong>Línea descendente:</strong> Dificultades acumulativas</li>
                <li><strong>Picos o valles:</strong> Eventos específicos que afectaron el rendimiento</li>
                <li><strong>Estabilidad:</strong> Consistencia en los resultados</li>
                <li>Compare con la <span style="color:red;font-weight:bold;">línea roja</span> para evaluar si se mantiene sobre el mínimo</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # Gráfico 5: Sistema de letras (si está activado)
        if usar_letras_prim or (nivel_educativo in ["Secundaria", "Ambos"] and usar_letras_sec):
            st.markdown("#### 🔠 Distribución por Sistema de Letras")

            if nivel_educativo == "Ambos":
                fig5 = px.sunburst(
                    df,
                    path=["Grado", "Letra"],
                    color="Letra",
                    color_discrete_map={
                        "AD": "#2E7D32",  # Verde oscuro
                        "A": "#4CAF50",    # Verde
                        "B": "#FFC107",    # Amarillo
                        "C": "#F44336",    # Rojo
                        "-": "#9E9E9E"     # Gris
                    },
                    labels={"Letra": "Categoría"}
                )
            else:
                fig5 = px.pie(
                    df,
                    names="Letra",
                    color="Letra",
                    color_discrete_map={
                        "AD": "#2E7D32",  # Verde oscuro
                        "A": "#4CAF50",    # Verde
                        "B": "#FFC107",    # Amarillo
                        "C": "#F44336",    # Rojo
                        "-": "#9E9E9E"     # Gris
                    },
                    hole=0.3,
                    labels={"Letra": "Categoría"}
                )

            st.plotly_chart(fig5, use_container_width=True)

            # Leyenda del gráfico
            st.markdown("""
            <div class="legend">
                <h4>📌 Escala de Letras:</h4>
                <table style="width:100%">
                    <tr>
                        <td><span style="color:#2E7D32;font-weight:bold;">AD (18-20):</span></td>
                        <td>Logro destacado (supera ampliamente lo esperado)</td>
                    </tr>
                    <tr>
                        <td><span style="color:#4CAF50;font-weight:bold;">A (14-17):</span></td>
                        <td>Logro esperado (cumple con los aprendizajes)</td>
                    </tr>
                    <tr>
                        <td><span style="color:#FFC107;font-weight:bold;">B (11-13):</span></td>
                        <td>En proceso (está alcanzando los aprendizajes)</td>
                    </tr>
                    <tr>
                        <td><span style="color:#F44336;font-weight:bold;">C (0-10):</span></td>
                        <td>En inicio (requiere mayor apoyo)</td>
                    </tr>
                </table>
                <p>En Secundaria, el sistema de letras es opcional (configurable en parámetros).</p>
            </div>
            """, unsafe_allow_html=True)

        # Nuevo Gráfico 6: Top 5 estudiantes
        st.markdown("#### 🏆 Top 5 Mejores Estudiantes por Grado")

        if nivel_educativo == "Ambos":
            top_estudiantes = pd.concat([
                df[df["Grado"].str.contains("Primaria")].nlargest(5, "Promedio"),
                df[df["Grado"].str.contains("Secundaria")].nlargest(5, "Promedio")
            ])
        else:
            top_estudiantes = df.nlargest(5, "Promedio")

        fig6 = px.bar(
            top_estudiantes,
            x="Estudiante",
            y="Promedio",
            color="Promedio",
            color_continuous_scale="Viridis",
            text="Promedio",
            hover_data=["Grado", "Asistencia"],
            labels={"Promedio": "Nota Promedio"},
            facet_col="Grado" if nivel_educativo == "Ambos" else None
        )
        fig6.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig6.update_layout(yaxis_range=[0, 20])
        st.plotly_chart(fig6, use_container_width=True)

        # Leyenda del gráfico
        st.markdown("""
        <div class="legend">
            <h4>📌 Buenas prácticas:</h4>
            <ul>
                <li>Identifique patrones comunes entre los estudiantes destacados</li>
                <li>Analice si hay correlación con asistencia, conducta u otros factores</li>
                <li>Considere crear grupos de tutoría donde los mejores apoyen a otros</li>
                <li>Reconozca públicamente los logros para motivar a todos</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tab3:
        st.markdown("### 🧑‍🎓 Análisis Individual")

        estudiante = st.selectbox(
            "Seleccione un estudiante",
            df["Estudiante"].unique(),
            key="estudiante_select"
        )

        datos = df[df["Estudiante"] == estudiante].iloc[0]

        # Tarjeta de resumen
        st.markdown(f"""
        <div style="background-color: #f5f5f5; border-radius: 10px; padding: 20px; margin-bottom: 20px;">
            <h3 style="color: #1f3c73;">{datos['Estudiante']}</h3>
            <p><strong>📋 DNI:</strong> {datos['DNI']} | <strong>🎓 Grado:</strong> {datos['Grado']}</p>
            <p><strong>📊 Promedio:</strong> {datos['Promedio']:.1f} {f"({datos['Letra']})" if datos['Letra'] != '-' else ""} |
            <strong>📅 Asistencia:</strong> {datos['Asistencia']}%</p>
            <p><strong>✅ Estado:</strong> <span style="color: {'#4CAF50' if datos['Estado'] == 'Aprobado' else '#F44336'}">{datos['Estado']}</span></p>
            <p><strong>📝 Conducta:</strong> {datos.get('Conducta', 'No registrada')}</p>
        </div>
        """, unsafe_allow_html=True)

        # Gráfico 7: Evolución individual
        st.markdown("#### 📶 Evolución Bimestral Individual")
        fig7 = go.Figure()

        fig7.add_trace(go.Scatter(
            x=["Bim1", "Bim2", "Bim3", "Bim4"],
            y=[datos["Bim1"], datos["Bim2"], datos["Bim3"], datos["Bim4"]],
            mode="lines+markers+text",
            name="Notas",
            line=dict(color="#1f3c73", width=3),
            marker=dict(size=12, color="#1f3c73"),
            text=[str(round(datos[b], 1)) for b in ["Bim1", "Bim2", "Bim3", "Bim4"]],
            textposition="top center"
        ))

        # Línea de aprobación según nivel
        nota_min = nota_minima_prim if "Primaria" in datos["Grado"] else nota_minima_sec
        fig7.add_hline(
            y=nota_min,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Mínimo aprobatorio: {nota_min}",
            annotation_position="bottom right"
        )

        fig7.update_layout(
            yaxis_range=[0, 20],
            yaxis_title="Nota",
            xaxis_title="Bimestre",
            showlegend=False
        )
        st.plotly_chart(fig7, use_container_width=True)

        # Leyenda del gráfico
        st.markdown("""
        <div class="legend">
            <h4>📌 Pautas de análisis:</h4>
            <ul>
                <li><strong>Tendencia:</strong> ¿Mejora, empeora o se mantiene?</li>
                <li><strong>Consistencia:</strong> ¿Grandes variaciones entre bimestres?</li>
                <li><strong>Puntos críticos:</strong> ¿Cuándo estuvo más bajo? ¿Coincide con eventos específicos?</li>
                <li><strong>Meta:</strong> ¿Siempre sobre el mínimo? ¿Se acerca a la excelencia?</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

         # Análisis con Claude API
        st.markdown("#### 🧠 Análisis Pedagógico con IA")

        if ANTHROPIC_API_KEY:
            if st.button("Generar Análisis", key="analisis_btn"):
                with st.spinner("Analizando con Claude AI..."):
                    prompt = """
                    [Texto del prompt permanece igual...]
                    """

                    headers = {
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    }

                    payload = {
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 2000,
                        "messages": [{"role": "user", "content": prompt}]
                    }

                    try:
                        response = requests.post(
                            "https://api.anthropic.com/v1/messages",
                            headers=headers,
                            json=payload,
                            timeout=30
                        )

                        if response.status_code == 200:
                            analisis = response.json()["content"][0]["text"]
                            # Solución alternativa para evitar problemas con f-strings
                            html_content = f"""
                            <div style="background-color: #e8f5e9; border-radius: 10px; padding: 15px; margin-top: 20px;">
                                <h4 style="color: #1f3c73;">🔍 Análisis Generado:</h4>
                                <div style="white-space: pre-wrap;">{analisis}</div>
                            </div>
                            """
                            st.markdown(html_content, unsafe_allow_html=True)
                        else:
                            st.error(f"Error al conectar con la API de Claude. Código: {response.status_code}")
                    except Exception as e:
                        st.error(f"Error de conexión: {str(e)}")
        else:
            st.warning("Ingrese su API Key de Claude en el panel izquierdo para habilitar el análisis con IA")

    with tab4:
        st.markdown("### 📄 Generar Reportes")

        estudiantes_seleccionados = st.multiselect(
            "Seleccione estudiantes para el reporte",
            df["Estudiante"].unique(),
            key="reporte_select"
        )

        if estudiantes_seleccionados:
            if st.button("Generar Reporte PDF", key="reporte_btn"):
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)

                for estudiante in estudiantes_seleccionados:
                    datos = df[df["Estudiante"] == estudiante].iloc[0]

                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, f"Reporte Académico - {estudiante}", 0, 1, 'C')
                    pdf.ln(8)

                    pdf.set_font("Arial", '', 12)
                    pdf.cell(0, 10, f"Grado: {datos['Grado']} | DNI: {datos['DNI']}", 0, 1)
                    pdf.cell(0, 10, f"Periodo: {periodo}", 0, 1)
                    pdf.ln(10)

                    # Tabla de notas
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(45, 10, "Bimestre", 1, 0, 'C')
                    pdf.cell(35, 10, "Nota (0-20)", 1, 0, 'C')
                    if datos['Letra'] != '-':
                        pdf.cell(35, 10, "Escala", 1, 0, 'C')
                    pdf.ln()

                    pdf.set_font("Arial", '', 12)
                    for i, bim in enumerate(["Bim1", "Bim2", "Bim3", "Bim4"], 1):
                        pdf.cell(45, 10, f"Bimestre {i}", 1, 0, 'C')
                        pdf.cell(35, 10, str(datos[bim]), 1, 0, 'C')
                        if datos['Letra'] != '-':
                            pdf.cell(35, 10, convertir_a_letras(datos[bim], "Primaria" if "Primaria" in datos["Grado"] else "Secundaria"), 1, 0, 'C')
                        pdf.ln()

                    pdf.ln(8)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(45, 10, "Promedio Final", 0, 0)
                    pdf.cell(35, 10, f"{datos['Promedio']:.1f}", 0, 0)
                    if datos['Letra'] != '-':
                        pdf.cell(35, 10, datos["Letra"], 0, 0)
                    pdf.ln(12)

                    pdf.cell(0, 10, f"Asistencia: {datos['Asistencia']}% | Estado: {datos['Estado']}", 0, 1)
                    pdf.ln(10)

                    # Recomendaciones
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, "Recomendaciones:", 0, 1)
                    pdf.set_font("Arial", '', 12)

                    if datos['Estado'] == 'Aprobado':
                        pdf.multi_cell(0, 8, "El estudiante ha alcanzado los objetivos de aprendizaje establecidos. Se recomienda:")
                        pdf.multi_cell(0, 8, "- Continuar con las estrategias pedagógicas actuales")
                        pdf.multi_cell(0, 8, "- Mantener el buen desempeño y asistencia")
                        pdf.multi_cell(0, 8, "- Proponer desafíos adicionales para alcanzar logros destacados")
                    else:
                        pdf.multi_cell(0, 8, "El estudiante requiere apoyo en las siguientes áreas:")
                        pdf.multi_cell(0, 8, "- Asistir a sesiones de reforzamiento en los bimestres con menor rendimiento")
                        pdf.multi_cell(0, 8, "- Implementar estrategias de aprendizaje personalizadas")
                        pdf.multi_cell(0, 8, "- Mejorar hábitos de estudio y participación en clase")
                        pdf.multi_cell(0, 8, "- Revisar causas de inasistencia si aplica")

                    pdf.ln(15)

                # Generar PDF
                pdf_bytes = pdf.output(dest='S').encode('latin1')
                st.download_button(
                    label="⬇️ Descargar Reporte Completo",
                    data=pdf_bytes,
                    file_name=f"reporte_academico_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    help="Descargue el reporte en formato PDF para imprimir o compartir"
                )
        else:
            st.warning("Seleccione al menos un estudiante para generar el reporte")

else:
    st.info("Por favor seleccione el modo de operación y configure los parámetros para continuar.")

# --- Pie de página ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>Sistema de Gestión Escolar © {0} - Ministerio de Educación del Perú</p>
    <p style="font-size: 0.8em;">Versión 2.2 | Desarrollado para el seguimiento pedagógico según normas MINEDU</p>
</div>
""".format(datetime.datetime.now().year), unsafe_allow_html=True)
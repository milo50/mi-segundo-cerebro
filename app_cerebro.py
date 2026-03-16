import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import gspread
import os
from google.oauth2.service_account import Credentials

# ==========================================
# 1. CONEXIÓN INTELIGENTE (LOCAL / NUBE)
# ==========================================
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

try:
    # 1. Intenta ejecutarse en tu computadora local
    directorio_actual = os.path.dirname(__file__)
    ruta_credenciales = os.path.join(directorio_actual, 'credenciales.json')
    CREDENCIALES = Credentials.from_service_account_file(ruta_credenciales, scopes=SCOPES)
except Exception:
    # 2. Si está en internet, saca la llave de la bóveda secreta de Streamlit
    credenciales_dict = dict(st.secrets["gcp_service_account"])
    CREDENCIALES = Credentials.from_service_account_info(credenciales_dict, scopes=SCOPES)

cliente = gspread.authorize(CREDENCIALES)

# Abrimos tu base de datos
DOCUMENTO = cliente.open('Base_Datos_Cerebro')
ws_pendientes = DOCUMENTO.worksheet('Pendientes')
ws_tracker = DOCUMENTO.worksheet('Tracker')
ws_ideas = DOCUMENTO.worksheet('Ideas')

def leer_hoja(worksheet, columnas):
    valores = worksheet.get_all_values()
    if len(valores) <= 1:
        return pd.DataFrame(columns=columnas)
    return pd.DataFrame(valores[1:], columns=valores[0])

def guardar_hoja_completa(worksheet, df):
    worksheet.clear()
    df_str = df.astype(str)
    worksheet.update("A1", [df_str.columns.values.tolist()] + df_str.values.tolist())

# ==========================================
# 2. CONFIGURACIÓN VISUAL Y ALERTAS
# ==========================================
st.set_page_config(page_title="Segundo Cerebro", page_icon="🧠", layout="centered")

df_pendientes = leer_hoja(ws_pendientes, ["Tarea", "Fecha_Limite", "Completada"])
df_pendientes['Completada'] = df_pendientes['Completada'].apply(lambda x: True if str(x).upper() == 'TRUE' else False)

tareas_activas = df_pendientes[df_pendientes["Completada"] == False]

if not tareas_activas.empty:
    cantidad = len(tareas_activas)
    st.toast(f"🔔 Tienes {cantidad} tareas pendientes", icon="🔔")

st.title("🧠 Mi Cerebro en la Nube")
st.markdown("---") 

tab1, tab2, tab3, tab4 = st.tabs(["✅ Pendientes", "⏱️ Tracker", "💡 Ideas", "🔍 Buscar"])

# ==========================================
# PESTAÑA 1: TAREAS PENDIENTES
# ==========================================
with tab1:
    st.header("Mis Tareas Pendientes")
    with st.form("form_nuevo_pendiente", clear_on_submit=True):
        nueva_tarea = st.text_input("Nueva tarea:")
        col1, col2, col3 = st.columns(3)
        with col1: fecha_tarea = st.date_input("Día:")
        with col2: hora_tarea = st.time_input("Hora de inicio:")
        with col3: duracion = st.number_input("Duración (minutos):", min_value=5, value=30, step=5)
        submit_pendiente = st.form_submit_button("➕ Agregar a la lista")
        
    if submit_pendiente and nueva_tarea:
        inicio_exacto = datetime.datetime.combine(fecha_tarea, hora_tarea)
        fin_exacto = inicio_exacto + datetime.timedelta(minutes=duracion)
        
        ws_pendientes.append_row([nueva_tarea, inicio_exacto.strftime("%Y-%m-%d %H:%M"), "FALSE"])
        st.success(f"¡Sincronizado en la nube!")
        
        str_inicio = inicio_exacto.strftime("%Y%m%dT%H%M%S")
        str_fin = fin_exacto.strftime("%Y%m%dT%H%M%S")
        enlace_gcal = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={urllib.parse.quote(nueva_tarea)}&dates={str_inicio}/{str_fin}&details={urllib.parse.quote('Generado por mi Segundo Cerebro')}&ctz=America/Mexico_City"

        st.link_button("📅 Guardar en Google Calendar", url=enlace_gcal, type="primary")

    st.markdown("---")
    df_mostrar = leer_hoja(ws_pendientes, ["Tarea", "Fecha_Limite", "Completada"])
    df_mostrar['Completada'] = df_mostrar['Completada'].apply(lambda x: True if str(x).upper() == 'TRUE' else False)
    
    if not df_mostrar.empty:
        df_editado = st.data_editor(
            df_mostrar,
            column_config={"Completada": st.column_config.CheckboxColumn("¿Listo?", default=False)},
            disabled=["Tarea", "Fecha_Limite"],
            hide_index=True,
            use_container_width=True
        )
        
        if not df_editado.equals(df_mostrar):
            guardar_hoja_completa(ws_pendientes, df_editado)
            st.rerun()
    else:
        st.info("No tienes tareas pendientes.")

# ==========================================
# PESTAÑA 2, 3 y 4: (Iguales)
# ==========================================
with tab2:
    st.header("Registrar Productividad")
    with st.form("form_tareas", clear_on_submit=True):
        tarea = st.text_input("¿Qué tarea realizaste?")
        minutos = st.number_input("Minutos invertidos:", min_value=1, step=1)
        eficiencia = st.slider("Nivel de eficiencia (1-10):", 1, 10, 8)
        submit_tarea = st.form_submit_button("Guardar Tarea")
        if submit_tarea and tarea:
            ws_tracker.append_row([datetime.datetime.now().strftime("%Y-%m-%d"), tarea, minutos, eficiencia])
            st.success(f"✅ ¡Tracker sincronizado en la nube!")

with tab3:
    st.header("Capturar Conocimiento")
    with st.form("form_ideas", clear_on_submit=True):
        categoria = st.text_input("Categoría o Proyecto")
        contenido = st.text_area("Desarrolla tu idea o aprendizaje:")
        submit_idea = st.form_submit_button("Guardar en la Bóveda")
        if submit_idea and categoria and contenido:
            ws_ideas.append_row([datetime.datetime.now().strftime("%Y-%m-%d"), categoria, contenido])
            st.success("🧠 ¡Idea sincronizada en la nube!")

with tab4:
    st.header("Buscador de Conocimiento")
    busqueda = st.text_input("Escribe una palabra clave para buscar:")
    if busqueda:
        df_ideas = leer_hoja(ws_ideas, ["Fecha", "Categoria", "Contenido"])
        resultados = df_ideas[df_ideas["Categoria"].str.contains(busqueda, case=False, na=False) | df_ideas["Contenido"].str.contains(busqueda, case=False, na=False)]
        if resultados.empty: st.warning("Sin resultados.")
        else: st.dataframe(resultados, use_container_width=True)
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import io
from datetime import datetime as dt 
import pytz

# Configuración del Dashboard
st.set_page_config(
    page_title="Dashboard Petróleo y Dolar",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Variación del Precio del Petróleo y del Dolar")
st.markdown("### Se realizará la visualización del precio del petróleo y del dolar en tiempo real")
st.write("Datos extraídos de forma pública a través de Yahoo Finance")


# 1. Interfaz de usuario: Selector de Crudo y Rango de Tiempo
col1, col2, col3 = st.columns(3)

with col1: 
    tipo_cambio = st.selectbox(
        "Selecciona el tipo de cambio:",
        ["Dolar a Peso","Pesos a Dolar" ]
    )
    
with col2:
    tipo_petroleo = st.selectbox(
        "Selecciona el tipo de crudo:",
        ["Petróleo WTI (Texas)", "Petróleo Brent (Europa)"]
    )

with col3:
    temporalidad = st.selectbox(
        "Selecciona el rango de tiempo histórico:",
        ["1 Día","1 Semana","1 Mes", "3 Meses", "6 Meses", "1 Año"],
        index=1
    )
    
# Mapeo de parámetros para la consulta
ticker = "CL=F" if "WTI" in tipo_petroleo else "BZ=F"
tick = "CLPUSD=X" if tipo_cambio == "Pesos a Dolar" else "USDCLP=X"
periodo_map = {"1 Día":"1d","1 Semana" :"5d","1 Mes": "1mo", "3 Meses": "3mo", "6 Meses": "6mo", "1 Año": "1y"}
periodo = periodo_map[temporalidad]

if  periodo == "1d":
    intervalo = "5m"          # Datos cada 5 minutos para el día de hoy
    formato_fecha = "%H:%M"    # Muestra solo la hora (Ej: 14:30)
elif periodo == "5d":
    intervalo = "60m"         # Datos cada hora para la semana, logrando un gráfico continuo y estético
    formato_fecha = "%d %b %H:%M" # Muestra día, mes abreviado y hora (Ej: 15 Sep 10:00)
else:
    intervalo = "1d"          # Datos diarios para rangos de un mes o más
    formato_fecha = "%d-%m-%Y" # Muestra la fecha estándar (Ej: 15-09-2026)
try:
    # 2. Descarga de datos históricos desde Yahoo Finance
    with st.spinner("Descargando datos del mercado..."):
        # Descarga los datos con un intervalo diario
        data = yf.download(ticker, period = periodo, interval = intervalo)
        df = yf.download(tick, period = periodo, interval = intervalo)
        # RESPALDO: Si seleccionó 1 Día y el mercado está cerrado (vacío), ampliamos a 3 días
        if periodo == "1d" and (data.empty or df.empty):
            data = yf.download(ticker, period="3d", interval="5m", multi_level_index=False)
            df = yf.download(tick, period="3d", interval="5m", multi_level_index=False)
            st.warning("⚠️ Mercados cerrados. Mostrando últimos datos intradía disponibles (Ventana de 3 días).")
    if not data.empty and not df.empty:
        st.success("✅ ¡Datos cargados correctamente de forma pública!")
        # Yahoo Finance a veces devuelve MultiIndex en las columnas, lo aplanamos
        if isinstance(data.columns, pd.MultiIndex) :
            data.columns = data.columns.get_level_values(0)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # 3. Procesamiento y Limpieza de Datos con Pandas
        data = data.reset_index()
        df = df.reset_index()
      
        columna_fecha_original = 'Datetime' if 'Datetime' in data.columns else 'Date'   
        # --- CORRECCIÓN DE ZONA HORARIA LOCAL ---
        # Detectamos la zona horaria del sistema donde corre la app (Local)
        zona_local = dt.now().astimezone().tzinfo
        
        for frame in [data, df]:
            if pd.api.types.is_datetime64_any_dtype(frame[columna_fecha_original]):
                # Si no tiene zona horaria asignada (tz-naive), le asignamos UTC (que usa yfinance por defecto en intradía)
                if frame[columna_fecha_original].dt.tz is None:
                    frame[columna_fecha_original] = frame[columna_fecha_original].dt.tz_localize('UTC')
                # Convertimos a la zona horaria local del entorno de ejecución
                frame[columna_fecha_original] = frame[columna_fecha_original].dt.tz_convert(zona_local)
         # Renombrar columnas para mayor claridad
        data = data[[columna_fecha_original, 'Close', 'Open', 'High', 'Low', 'Volume']]
        data.columns = ['Fecha', 'Cierre', 'Apertura', 'Máximo', 'Mínimo', 'Volumen']
       
        df = df[[columna_fecha_original, 'Close', 'Open', 'High', 'Low', 'Volume']]
        df.columns = ['Fecha', 'Cierre', 'Apertura', 'Máximo', 'Mínimo', 'Volumen']
         # --- KPI's ---
        kpi_col1, kpi_col2 = st.columns(2)
        with kpi_col1:
            # Corregido: Variables redefinidas correctamente para Petróleo
            petroleo_ultimo = float(data['Cierre'].iloc[-1])
            petroleo_anterior = float(data['Cierre'].iloc[-2]) if len(data) > 1 else petroleo_ultimo
            variacion_petroleo = petroleo_ultimo - petroleo_anterior
            
            st.metric(
                label=f"Último Precio ({tipo_petroleo})", 
                value=f"${petroleo_ultimo:,.2f} USD",
                delta=f"${variacion_petroleo:,.2f} USD vs anterior"
            )
            
        with kpi_col2:
            # Corregido: Variables redefinidas correctamente para Divisa
            divisa_ultima = float(df['Cierre'].iloc[-1])
            divisa_anterior = float(df['Cierre'].iloc[-2]) if len(df) > 1 else divisa_ultima
            delta_divisa = divisa_ultima - divisa_anterior
            
            # Formato dinámico según la divisa seleccionada
            simbolo_moneda = "USD" if tipo_cambio == "Pesos a Dolar" else "CLP"
            st.metric(
                label=f"Último Precio ({tipo_cambio})", 
                value=f"{divisa_ultima:,.4f} {simbolo_moneda}",
                delta=f"{delta_divisa:,.4f} {simbolo_moneda} vs anterior"
            )

       
               
         # Gráfico 1: Petróleo
        fig_petroleo = px.line(
            data, 
            x="Fecha", 
            y="Cierre", 
            title=f"Evolución del Precio de Cierre - {temporalidad} ({tipo_petroleo})",
            labels={"Fecha": "Fecha de Cotización", "Cierre": "Precio por Barril (USD)"},
            markers=(periodo in ["1d", "5d"]) 
        )
        fig_petroleo.update_traces(line_color="blue")
        fig_petroleo.update_layout(hovermode="x unified", template="plotly_white", title_font_size=20)
        fig_petroleo.update_xaxes(tickformat=formato_fecha)
        st.plotly_chart(fig_petroleo, use_container_width=True)
        
        # Gráfico 2: Divisa (Corregido: Antes graficaba 'data' en vez de 'df')
        fig_divisa = px.line(
            df, 
            x="Fecha", 
            y="Cierre", 
            title=f"Evolución del Tipo de Cambio - {temporalidad} ({tipo_cambio})",
            labels={"Fecha": "Fecha de Cotización", "Cierre": f"Valor ({simbolo_moneda})"},
            markers=(periodo in ["1d", "5d"]) 
        )
        fig_divisa.update_traces(line_color="red")
        fig_divisa.update_layout(hovermode="x unified", template="plotly_white", title_font_size=20)
        fig_divisa.update_xaxes(tickformat=formato_fecha)
        st.plotly_chart(fig_divisa, use_container_width=True)
        # 5. Mostrar Tabla de Datos expandible y Botones de Descarga
        with st.expander("👀 Ver tabla con el histórico de datos "):
            tab1, tab2 = st.tabs(["Datos Petróleo", "Datos Divisas"])
                      
            # Creamos dos columnas dentro del expansor para los botones
          
            with tab1:
                    # 1. Preparación del archivo .CSV (Soporta zonas horarias sin problemas)
                    df_ordenado = data.sort_values(by="Fecha", ascending=False)
                    st.dataframe(df_ordenado, use_container_width=True)
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                      csv_data = df_ordenado.to_csv(index=False).encode('utf-8')
                      st.download_button(
                        label="📥 Descargar formato .CSV",
                        data=csv_data,
                        file_name=f"historico_petroleo_{ticker}.csv",
                        mime="text/csv",
                        use_container_width=True
                      )
                    with btn_col2:
                # 2. Preparación del archivo .XLSX (Excel) en memoria usando BytesIO
                      import io
                
                # Creamos una copia de los datos para Excel para no afectar el gráfico principal
                      df_excel = df_ordenado.copy()
                
                # CORRECCIÓN CRÍTICA: Remover la zona horaria de las fechas si es que existe
                      if pd.api.types.is_datetime64_any_dtype(df_excel['Fecha']):
                        df_excel['Fecha'] = df_excel['Fecha'].dt.tz_localize(None)
                
                      buffer = io.BytesIO()
                      with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    # Guardamos los datos limpios en el archivo virtual
                       df_excel.to_excel(writer, index=False, sheet_name='Datos_Petroleo')
                
                # Extraemos el valor binario del archivo generado
                      excel_data = buffer.getvalue()
                
                      st.download_button(
                        label="📊 Descargar formato .XLSX (Excel)",
                        data=excel_data,
                        file_name=f"historico_petroleo_{ticker}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                        )
            with tab2:
                    d_ordenado = df.sort_values(by="Fecha", ascending=False)
                    st.dataframe(d_ordenado, use_container_width=True)
                   
                    bt_col1, bt_col2 = st.columns(2)
                    with bt_col1:
                # 1. Preparación del archivo .CSV (Soporta zonas horarias sin problemas)
                    
                      csv_data = d_ordenado.to_csv(index=False).encode('utf-8')
                      st.download_button(
                        label="📥 Descargar formato .CSV",
                        data=csv_data,
                        file_name=f"historico_divisas_{tick}.csv",
                        mime="text/csv",
                        use_container_width=True
                        )
                    with bt_col2:
                # 2. Preparación del archivo .XLSX (Excel) en memoria usando BytesIO
                      import io
                
                # Creamos una copia de los datos para Excel para no afectar el gráfico principal
                      d_excel = d_ordenado.copy()
                
                # CORRECCIÓN CRÍTICA: Remover la zona horaria de las fechas si es que existe
                      if pd.api.types.is_datetime64_any_dtype(d_excel['Fecha']):
                       d_excel['Fecha'] = d_excel['Fecha'].dt.tz_localize(None)
                
                      buffer = io.BytesIO()
                      with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    # Guardamos los datos limpios en el archivo virtual
                       d_excel.to_excel(writer, index=False, sheet_name='Datos_Divisas')
                
                # Extraemos el valor binario del archivo generado
                      excel_data = buffer.getvalue()
                
                      st.download_button(
                        label="📊 Descargar formato .XLSX (Excel)",
                        data=excel_data,
                        file_name=f"historico_divisas_{tick}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                        )
           
            
    else:
        st.error("❌ No se encontraron registros financieros para este símbolo.")
        
except Exception as e:
    st.error(f"💥 Error inesperado al procesar los datos: {e}")

            

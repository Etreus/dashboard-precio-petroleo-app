import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# Configuración del Dashboard
st.set_page_config(
    page_title="Dashboard Petróleo",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Variación del Precio del Petróleo")
st.markdown("### Se realizará la visualización del precio del petróleo en tiempo real")
st.write("Datos extraídos de forma pública a través de Yahoo Finance")

# 1. Interfaz de usuario: Selector de Crudo y Rango de Tiempo
col1, col2 = st.columns(2)

with col1:
    tipo_petroleo = st.selectbox(
        "Selecciona el tipo de crudo:",
        ["Petróleo WTI (Texas)", "Petróleo Brent (Europa)"]
    )

with col2:
    temporalidad = st.selectbox(
        "Selecciona el rango de tiempo histórico:",
        ["1 Día","1 Semana","1 Mes", "3 Meses", "6 Meses", "1 Año"],
        index=1
    )
    
# Mapeo de parámetros para la consulta
ticker = "CL=F" if "WTI" in tipo_petroleo else "BZ=F"
periodo_map = {"1 Día":"1d","1 Semana" :"5d","1 Mes": "1mo", "3 Meses": "3mo", "6 Meses": "6mo", "1 Año": "1y"}
periodo = periodo_map[temporalidad]

if periodo == "1d":
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
        data = yf.download(ticker, period=periodo, interval= intervalo)
    if not data.empty:
        st.success("✅ ¡Datos cargados correctamente de forma pública!")
        
        # 3. Procesamiento y Limpieza de Datos con Pandas
        data = data.reset_index()
      
        # Yahoo Finance a veces devuelve MultiIndex en las columnas, lo aplanamos
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        columna_fecha_original = 'Datetime' if 'Datetime' in data.columns else 'Date'   
         # Renombrar columnas para mayor claridad
        data = data[[columna_fecha_original, 'Close', 'Open', 'High', 'Low', 'Volume']]
        data.columns = ['Fecha', 'Cierre', 'Apertura', 'Máximo', 'Mínimo', 'Volumen']
        
        # Obtener el último precio disponible para la métrica
        ultimo_precio = float(data['Cierre'].iloc[-1].item())
        precio_anterior = float(data['Cierre'].iloc[-2].item())
        variacion = ultimo_precio - precio_anterior
        # Desplegar KPI principal
        st.metric(
            label=f"Último Precio de Cierre ({tipo_petroleo})", 
            value=f"${ultimo_precio:,.2f} USD",
            delta=f"${variacion:,.2f} USD respecto al día anterior"
        )
        
          # 4. Construcción del Gráfico Interactivo con Plotly
                # 4. Construcción del Gráfico Interactivo con Plotly
        fig = px.line(
            data, 
            x="Fecha", 
            y="Cierre", 
            title=f"Evolución del Precio de Cierre - {temporalidad} ({tipo_petroleo})",
            labels={"Fecha": "Fecha de Cotización", "Cierre": "Precio por Barril (USD)"},
            # CORRECCIÓN 1: Evita que se amontonen los puntos en rangos largos
            # Solo dibuja círculos si el período seleccionado es corto ("1 Día" o "1 Semana")
            markers=(periodo in ["1d", "5d"]) 
        )
        fig.update_traces(line_color="red")
        # Personalización visual del gráfico
        fig.update_layout(
            hovermode="x unified",
            template="plotly_white",
            title_font_size=20
        )
        
        # CORRECCIÓN 2: Aplica el formato dinámico al eje X (Muestra horas en intradía y fechas en históricos)
        fig.update_xaxes(tickformat=formato_fecha)
        
        # Mostrar gráfico en ancho completo
        st.plotly_chart(fig, use_container_width=True)
        # 5. Mostrar Tabla de Datos expandible y Botones de Descarga
        with st.expander("👀 Ver tabla con el histórico de datos )"):
            
            # Ordenamos los datos para mostrar lo más reciente arriba
            df_ordenado = data.sort_values(by="Fecha", ascending=False)
            
            # Creamos dos columnas dentro del expansor para los botones
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                # 1. Preparación del archivo .CSV (Soporta zonas horarias sin problemas)
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
            
            # Desplegar la tabla interactiva abajo de los dos botones
            st.dataframe(df_ordenado, use_container_width=True)
            
    else:
        st.error("❌ No se encontraron registros financieros para este símbolo.")
        
except Exception as e:
    st.error(f"💥 Error inesperado al procesar los datos: {e}")

            

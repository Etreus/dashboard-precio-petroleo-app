
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import io
from datetime import datetime as dt 
import pytz

# Configuración del Dashboard
st.set_page_config(
    page_title="Dashboard Dólar, Petróleo y Cobre",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Variación del Precio del Dólar, Petróleo y del Cobre ")
st.markdown("### Se realizará la visualización del precio del dólar, del petróleo y del cobre en tiempo real")
st.write("Datos extraídos de forma pública a través de Yahoo Finance")


# 1. Interfaz de usuario: Selector de Crudo y Rango de Tiempo
col1, col2, col3 = st.columns(3)

with col1: 
    tipo_cambio = st.selectbox(
        "Selecciona el tipo de cambio:",
        ["Dólar a Peso","Pesos a Dólar" ]
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
tick = "CLPUSD=X" if tipo_cambio == "Pesos a Dólar" else "USDCLP=X"
ticker_cobre = "HG=F"  # Futuros de Cobre en COMEX
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
        data_cobre = yf.download(ticker_cobre, period=periodo, interval=intervalo, multi_level_index=False)
        # RESPALDO: Si seleccionó 1 Día y el mercado está cerrado (vacío), ampliamos a 3 días
        if periodo == "1d" and (data.empty or df.empty):
            data = yf.download(ticker, period="3d", interval="5m", multi_level_index=False)
            df = yf.download(tick, period="3d", interval="5m", multi_level_index=False)
            data_cobre = yf.download(ticker_cobre, period="3d", interval="5m", multi_level_index=False)
            st.warning("⚠️ Uno o más mercados cerrados. Mostrando últimos datos intradía disponibles, ventana de 3 días.")
    if not data.empty and not df.empty:
        st.success("✅ ¡Datos cargados correctamente de forma pública!")
        # Yahoo Finance a veces devuelve MultiIndex en las columnas, lo aplanamos
        if isinstance(data.columns, pd.MultiIndex) :
            data.columns = data.columns.get_level_values(0)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if isinstance(df.columns, pd.MultiIndex):
            data_cobre.columns = data_cobre.columns.get_level_values(0)
            
        # 3. Procesamiento y Limpieza de Datos con Pandas
        data = data.reset_index()
        df = df.reset_index()
        data_cobre= data_cobre.reset_index()
        columna_fecha_original = 'Datetime' if 'Datetime' in data.columns else 'Date'   
        # --- CORRECCIÓN DE ZONA HORARIA LOCAL ---
        # Detectamos la zona horaria del sistema donde corre la app (Local)
        zona_local = dt.now().astimezone().tzinfo
        
        for frame in [data, df, data_cobre]:
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
        
        data_cobre = data_cobre[[columna_fecha_original, 'Close', 'Open', 'High', 'Low', 'Volume']]
        data_cobre.columns = ['Fecha', 'Cierre', 'Apertura', 'Máximo', 'Mínimo', 'Volumen']
        
        # CORRECCIÓN DE UNIDAD PARA EL COBRE: Convertir de centavos (US¢) a Dólares puros (USD)
        for col in ['Cierre', 'Apertura', 'Máximo', 'Mínimo']:
            data_cobre[col] = data_cobre[col] / 100.0
        # --- LÓGICA DEL ESTADO DEL MERCADO ---
        tz_ny = pytz.timezone('America/New_York')
        ahora_ny = dt.now(tz_ny)
        dia_semana_ny = ahora_ny.weekday() # 0=Lunes, 4=Viernes, 5=Sábado, 6=Domingo
        hora_ny = ahora_ny.hour

         # 1. Estado para los Commodities (Aplica idéntico para Petróleo y Cobre)
        if dia_semana_ny == 5: # Sábado cerrado
            mercado_commodities_abierto = False
        elif dia_semana_ny == 4 and hora_ny >= 17: # Viernes cierra a las 17:00 EST
            mercado_commodities_abierto = False
        elif dia_semana_ny == 6 and hora_ny < 18: # Domingo abre a las 18:00 EST
            mercado_commodities_abierto = False
        elif hora_ny == 17: # Receso técnico diario de 17:00 a 18:00 EST (Lun a Jue)
            mercado_commodities_abierto = False
        else:
            mercado_commodities_abierto = True

        # 2. Estado del Mercado del Dólar (Interbancario en Chile o Forex Global)
        # Forzamos la zona horaria de Chile para evaluar el mercado interbancario local
        tz_cl = pytz.timezone('America/Santiago')
        ahora_cl = dt.now(tz_cl)
        dia_semana_cl = ahora_cl.weekday()
        hora_cl = ahora_cl.hour
        minuto_cl = ahora_cl.minute

        if tipo_cambio == "Dólar a Peso":
            # CORRECCIÓN AQUÍ: Evaluamos correctamente si es Sábado (5) o Domingo (6)
            if dia_semana_cl in [5,6]: 
                divisa_abierta = False
            elif 9 <= hora_cl < 14:
                divisa_abierta = True
            else:
                divisa_abierta = False
        else:
            # Forex Internacional (Pesos a Dólar): Abierto continuo desde Domingo 17:00 EST a Viernes 17:00 EST
            if dia_semana_ny == 5:
                divisa_abierta = False
            elif dia_semana_ny == 4 and hora_ny >= 17:
                divisa_abierta = False
            elif dia_semana_ny == 6 and hora_ny < 17:
                divisa_abierta = False
            else:
                divisa_abierta = True

        # Renderizar indicadores visuales organizados en columnas
        ind_col1, ind_col2, ind_col3 = st.columns(3)
        with ind_col2:
            st.markdown(f"**Petróleo ({tipo_petroleo}):** " + ("🟢 **ABIERTO**" if mercado_commodities_abierto else "🔴 **CERRADO**"))
        with ind_col3:
            st.markdown(f"**Cobre (COMEX):** " + ("🟢 **ABIERTO**" if mercado_commodities_abierto else "🔴 **CERRADO**"))
        with ind_col1:
            if divisa_abierta:
                st.markdown(f"**Mercado Divisa ({tipo_cambio}):** 🟢 **ABIERTO**")
            else:
                if tipo_cambio == "Dólar a Peso":
                    st.markdown(f"**Mercado Divisa ({tipo_cambio}):** 🔴 **CERRADO** (Horario bancario: Lun a Vie 09:00 a 14:00)")
                else:
                    st.markdown(f"**Mercado Divisa ({tipo_cambio}):** 🔴 **CERRADO** (Cierre de fin de semana)")
        
         # --- KPI's ---
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col2:
            # Corregido: Variables redefinidas correctamente para Petróleo
            petroleo_ultimo = float(data['Cierre'].iloc[-1].item())
            petroleo_anterior = float(data['Cierre'].iloc[0].item()) if len(data) > 1 else petroleo_ultimo
            variacion_petroleo = petroleo_ultimo - petroleo_anterior
            
            st.metric(
                label=f"Último Precio ({tipo_petroleo})", 
                value=f"${petroleo_ultimo:,.2f} USD",
                delta=float(round(variacion_petroleo, 2)) ,
                help=f"Variación de ${variacion_petroleo:,.2f} USD vs el inicio del periodo seleccionado"
                
            )
            
        with kpi_col3:  # Cobre al extremo derecho
            cobre_ultimo = float(data_cobre['Cierre'].iloc[-1].item())
            cobre_anterior = float(data_cobre['Cierre'].iloc[0].item()) if len(data_cobre) > 1 else cobre_ultimo
            variacion_cobre = cobre_ultimo - cobre_anterior
            st.metric(
                label="Último Precio Cobre (COMEX)", 
                value=f"${cobre_ultimo:,.4f} USD/lb",
                delta=float(round(variacion_cobre, 4)),
                help=f"Variación vs inicio del periodo ({temporalidad})"
            )    
        with kpi_col1:
            # Corregido: Variables redefinidas correctamente para Divisa
            divisa_ultima = float(df['Cierre'].iloc[-1].item())
            divisa_anterior = float(df['Cierre'].iloc[0].item()) if len(df) > 1 else divisa_ultima
            delta_divisa = divisa_ultima - divisa_anterior
            
            # Formato dinámico según la divisa seleccionada
            simbolo_moneda = "USD" if tipo_cambio == "Pesos a Dolar" else "CLP"
            st.metric(
                label=f"Último Precio ({tipo_cambio})", 
                value=f"{divisa_ultima:,.4f} {simbolo_moneda}",
                delta=float(round(delta_divisa, 4)) , 
                help=f"Variación de {delta_divisa:,.4f} {simbolo_moneda} vs el inicio del periodo seleccionado"
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
        
        fig_cobre = px.line(data_cobre, x="Fecha", y="Cierre", 
                            title=f"Evolución del Cobre - {temporalidad} (COMEX)",
                            labels={"Fecha": "Fecha de Cotización", "Cierre": "Precio por Libra (USD)"},
                            markers=(periodo in ["1d", "5d"]))
        fig_cobre.update_traces(line_color="orange")
        fig_cobre.update_layout(hovermode="x unified", template="plotly_white", title_font_size=20)
        fig_cobre.update_xaxes(tickformat=formato_fecha)
        st.plotly_chart(fig_cobre, width="stretch")
        # 5. Mostrar Tabla de Datos expandible y Botones de Descarga
        with st.expander("👀 Ver tabla con el histórico de datos "):
            tab1, tab2, tab3 = st.tabs(["Datos Petróleo", "Datos Divisas", "Datos Cobre"])
                      
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
           
            with tab3:
                c_ordenado = data_cobre.sort_values(by="Fecha", ascending=False)
                
                c_mostrar = c_ordenado.copy()
                if pd.api.types.is_datetime64_any_dtype(c_mostrar['Fecha']):
                    c_mostrar['Fecha'] = c_mostrar['Fecha'].dt.strftime('%Y-%m-%d %H:%M:%S' if periodo in ["1d", "5d"] else '%Y-%m-%d')
                st.dataframe(c_mostrar, width="stretch")
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    csv_data_cobre = c_ordenado.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar formato .CSV",
                        data=csv_data_cobre,
                        file_name=f"historico_cobre_{ticker_cobre}.csv",
                        mime="text/csv",
                        width="stretch"
                    )
                with c_btn2:
                    c_excel = c_ordenado.copy()
                    if pd.api.types.is_datetime64_any_dtype(c_excel['Fecha']):
                        c_excel['Fecha'] = c_excel['Fecha'].dt.tz_localize(None)
                
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        c_excel.to_excel(writer, index=False, sheet_name='Datos_Cobre')
                
                    excel_data_cobre = buffer.getvalue()
                    st.download_button(
                        label="📊 Descargar formato .XLSX (Excel)",
                        data=excel_data_cobre,
                        file_name=f"historico_cobre_{ticker_cobre}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width="stretch"
                    )
    else:
        st.error("❌ No se encontraron registros financieros para este símbolo.")
        
except Exception as e:
    st.error(f"💥 Error inesperado al procesar los datos: {e}")        

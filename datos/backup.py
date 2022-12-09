# Aplicación desarrollada en Streamlit para visualización de datos de biodiversidad
# Autor: Manuel Vargas (mfvargas@gmail.com)
# Fecha de creación: 2022-11-19


import streamlit as st

import pandas as pd
import geopandas as gpd

import plotly.express as px

import folium
from folium import Marker
from folium.plugins import MarkerCluster
from folium.plugins import HeatMap
from streamlit_folium import folium_static

import math


#
# Configuración de la página
#
st.set_page_config(layout='wide')


#
# TÍTULO Y DESCRIPCIÓN DE LA APLICACIÓN
#

st.title('Visualización de datos de biodiversidad')
st.markdown('Esta aplicación presenta visualizaciones tabulares, gráficas y geoespaciales de datos de biodiversidad que siguen el estándar [Darwin Core (DwC)](https://dwc.tdwg.org/terms/).')
st.markdown('El usuario debe seleccionar un archivo CSV basado en el DwC y posteriormente elegir una de las especies con datos contenidos en el archivo. **El archivo debe estar separado por tabuladores**. Este tipo de archivos puede obtenerse, entre otras formas, en el portal de la [Infraestructura Mundial de Información en Biodiversidad (GBIF)](https://www.gbif.org/).')
st.markdown('La aplicación muestra un conjunto de tablas, gráficos y mapas correspondientes a la distribución de la especie en el tiempo y en el espacio.')


#
# ENTRADAS
#

# Carga de datos
archivo_registros_presencia = st.sidebar.file_uploader('Seleccione un archivo CSV que siga el estándar DwC')

# Se continúa con el procesamiento solo si hay un archivo de datos cargado
if archivo_registros_presencia is not None:
    # Carga de registros de presencia en un dataframe
    registros_presencia = pd.read_csv(archivo_registros_presencia, delimiter='\t')
    # Conversión del dataframe de registros de presencia a geodataframe
    registros_presencia = gpd.GeoDataFrame(registros_presencia, 
                                           geometry=gpd.points_from_xy(registros_presencia.decimalLongitude, 
                                                                       registros_presencia.decimalLatitude),
                                           crs='EPSG:4326')

    # Carga de polígonos de ASP
    asp = gpd.read_file("datos/asp.geojson")


    # Limpieza de datos
    # Eliminación de registros con valores nulos en la columna 'species'
    registros_presencia = registros_presencia[registros_presencia['species'].notna()]
    # Cambio del tipo de datos del campo de fecha
    registros_presencia["eventDate"] = pd.to_datetime(registros_presencia["eventDate"])

    # Especificación de filtros
    # Especie
    lista_especies = registros_presencia.species.unique().tolist()
    lista_especies.sort()
    filtro_especie = st.sidebar.selectbox('Seleccione la especie', lista_especies)


    #
    # PROCESAMIENTO
    #

    # Filtrado
    registros_presencia = registros_presencia[registros_presencia['species'] == filtro_especie]

    # Cálculo de la cantidad de registros en ASP
    # "Join" espacial de las capas de ASP y registros de presencia
    asp_contienen_registros = asp.sjoin(registros_presencia, how="left", predicate="contains")
    # Conteo de registros de presencia en cada ASP
    asp_registros = asp_contienen_registros.groupby("codigo").agg(cantidad_registros_presencia = ("gbifID","count"))
    asp_registros = asp_registros.reset_index() # para convertir la serie a dataframe


    #
    # SALIDAS
    #

    # Tabla de registros de presencia
    st.header('Registros de presencia')
    st.dataframe(registros_presencia[['family', 'species', 'eventDate', 'locality', 'occurrenceID']].rename(columns = {'family':'Familia', 'species':'Especie', 'eventDate':'Fecha', 'locality':'Localidad', 'occurrenceID':'Origen del dato'}))


    # Definición de columnas
    col1, col2 = st.columns(2)

    with col1:
        # Gráficos de historial de registros de presencia por año
        st.header('Historial de registros por año')
        registros_presencia_grp_anio = pd.DataFrame(registros_presencia.groupby(registros_presencia['eventDate'].dt.year).count().eventDate)
        registros_presencia_grp_anio.columns = ['registros_presencia']

        fig = px.bar(registros_presencia_grp_anio, 
                    labels={'eventDate':'Año', 'value':'Registros de presencia'})
        st.plotly_chart(fig)

    with col2:
        # Gráficos de estacionalidad de registros de presencia por mes
        st.header('Estacionalidad de registros por mes')
        registros_presencia_grp_mes = pd.DataFrame(registros_presencia.groupby(registros_presencia['eventDate'].dt.month).count().eventDate)
        registros_presencia_grp_mes.columns = ['registros_presencia']

        fig = px.area(registros_presencia_grp_mes, 
                    labels={'eventDate':'Mes', 'value':'Registros de presencia'})
        st.plotly_chart(fig)      


    # Gráficos de cantidad de registros de presencia por ASP
    # "Join" para agregar la columna con el conteo a la capa de ASP
    asp_registros = asp_registros.join(asp.set_index('codigo'), on='codigo', rsuffix='_b')
    # Dataframe filtrado para usar en graficación
    asp_registros_grafico = asp_registros.loc[asp_registros['cantidad_registros_presencia'] > 0, 
                                                            ["nombre_asp", "cantidad_registros_presencia"]].sort_values("cantidad_registros_presencia", ascending=[False]).head(15)
    asp_registros_grafico = asp_registros_grafico.set_index('nombre_asp')  

    with col1:
        st.header('Cantidad de registros por ASP')

        fig = px.bar(asp_registros_grafico, 
                    labels={'nombre_asp':'ASP', 'cantidad_registros_presencia':'Registros de presencia'})
        st.plotly_chart(fig)    

    with col2:        
        # st.subheader('px.pie()')        
        st.header('Porcentaje de registros por ASP')
        
        fig = px.pie(asp_registros_grafico, 
                    names=asp_registros_grafico.index,
                    values='cantidad_registros_presencia')
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig)    


    with col1:
        # Mapa de calor y de registros agrupados
        st.header('Mapa de calor y de registros agrupados')

        # Capa base
        m = folium.Map(location=[9.6, -84.2], tiles='CartoDB dark_matter', zoom_start=8)
        # Capa de calor
        HeatMap(data=registros_presencia[['decimalLatitude', 'decimalLongitude']],
                name='Mapa de calor').add_to(m)
        # Capa de ASP
        folium.GeoJson(data=asp, name='ASP').add_to(m)
        # Capa de registros de presencia agrupados
        mc = MarkerCluster(name='Registros agrupados')
        for idx, row in registros_presencia.iterrows():
            if not math.isnan(row['decimalLongitude']) and not math.isnan(row['decimalLatitude']):
                mc.add_child(Marker([row['decimalLatitude'], row['decimalLongitude']], 
                                    popup=row['species']))
        m.add_child(mc)
        # Control de capas
        folium.LayerControl().add_to(m)    
        # Despliegue del mapa
        folium_static(m)

    with col2:
        # Mapa de coropletas de registros de presencia en ASP
        st.header('Mapa de cantidad de registros en ASP')

        # Capa base
        m = folium.Map(location=[9.6, -84.2], tiles='CartoDB positron', zoom_start=8)
        # Capa de coropletas
        folium.Choropleth(
            name="Cantidad de registros en ASP",
            geo_data=asp,
            data=asp_registros,
            columns=['codigo', 'cantidad_registros_presencia'],
            bins=8,
            key_on='feature.properties.codigo',
            fill_color='Reds', 
            fill_opacity=0.5, 
            line_opacity=1,
            legend_name='Cantidad de registros de presencia',
            smooth_factor=0).add_to(m)
        # Control de capas
        folium.LayerControl().add_to(m)        
        # Despliegue del mapa
        folium_static(m)   

    # Mapa de registros de presencia
    st.header('Mapa de registros de presencia')
    st.map(registros_presencia.rename(columns = {'decimalLongitude':'longitude', 'decimalLatitude':'latitude'}))

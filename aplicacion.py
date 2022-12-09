# Aplicación desarrollada en Streamlit para visualización de datos de biodiversidad
# Autor: Manuel Vargas (mfvargas@gmail.com)
# Fecha de creación: 2022-11-19
# El código original fue adaptado para cantones por los estudiantes: Alexandra Salazar y David Young

#Version:0  =   commit 


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

# Carga de datos subidos por el usuario
datos_usuarios = st.sidebar.file_uploader('Seleccione un archivo CSV que siga el estándar DwC')

# Se continúa con el procesamiento solo si hay un archivo de datos cargado
if datos_usuarios is not None:
    # Carga de registros de presencia en un dataframe con nombre de "registros"
    registros = pd.read_csv(datos_usuarios, delimiter='\t')
    # Conversión del dataframe de registros de presencia a geodataframe, identifica en código las columnas de las coordenadas
    registros = gpd.GeoDataFrame(registros, 
                                           geometry=gpd.points_from_xy(registros.decimalLongitude, 
                                                                       registros.decimalLatitude),
                                           crs='EPSG:4326')

    # Carga de polígonos de los cantones
    can = gpd.read_file("datos/cantones/cantones.geojson")


    # Limpieza de datos
    # Eliminación de registros con valores nulos en la columna 'species'
    registros = registros[registros['species'].notna()]
    # Cambio del tipo de datos del campo de fecha
    registros["eventDate"] = pd.to_datetime(registros["eventDate"])

    # Especificación de filtros
    # Especie
    lista_especies = registros.species.unique().tolist()
    lista_especies.sort()
    filtro_especie = st.sidebar.selectbox('Seleccione la especie', lista_especies)


    #
    # PROCESAMIENTO
    #

    # Filtrado
    registros = registros[registros['species'] == filtro_especie]

    # Cálculo de la cantidad de registros en los cantones
    # "Join" espacial de las capas de cantones y registros de presencia de especies
    can_contienen_registros = can.sjoin(registros, how="left", predicate="contains")
    # Conteo de registros de presencia en cada cantón
    can_registros = can_contienen_registros.groupby("cod_canton").agg(cantidad_registros = ("gbifID","count"))
    can_registros = can_registros.reset_index() # para convertir la serie a dataframe


    #
    # SALIDAS ------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #

    # Tabla de registros de presencia (modifica la primer tabla que se muestra en la aplicación web)
    st.header('Registros de presencia de especies')
    st.dataframe(registros[['species', 'stateProvince', 'locality','eventDate']].rename(columns = {'species':'Especie', 'stateProvince':'Provincia', 'locality':'Localidad', 'eventDate':'Fecha'}))


    # Definición de columnas de la parte visual de nuestra aplicación, dividará el contenido en dos columnas
    col1, col2 = st.columns(2)

    with col1:
        # Gráficos de historial de registros de presencia por año
        st.header('Historial de registros por año')

        # Agrupación y suma
        suma_redvial_cantones = interseccion_redvial_cantones.groupby(["cod_canton"])["longitud_redvial"].sum()

        # Para convertir la serie en dataframe
        suma_redvial_cantones = suma_redvial_cantones.reset_index()

        suma_redvial_cantones
    '''    
        registros_grp_anio = pd.DataFrame(registros.groupby(registros['stateProvince']).count())
        registros_grp_anio.columns = ['registros']

        fig = px.bar(registros_grp_anio, 
                    labels={'stateProvince':'Provincia', 'value':'Cantidad de registros'})

    '''  
        st.plotly_chart(fig)

    with col2:
        # Gráficos de estacionalidad de registros de presencia por mes
        st.header('Estacionalidad de registros por mes')
        registros_grp_mes = pd.DataFrame(registros.groupby(registros['eventDate'].dt.month).count().eventDate)
        registros_grp_mes.columns = ['registros']

        fig = px.area(registros_grp_mes, 
                    labels={'eventDate':'Mes', 'value':'Registros de presencia'})
        st.plotly_chart(fig)      
'''

    # Gráficos de cantidad de registros de presencia por can
    # "Join" para agregar la columna con el conteo a la capa de can
    can_registros = can_registros.join(can.set_index('cod_canton'), on='cod_canton', rsuffix='_b')
    # Dataframe filtrado para usar en graficación
    can_registros_grafico = can_registros.loc[can_registros['cantidad_registros'] > 0, 
                                                            ["nombre_can", "cantidad_registros"]].sort_values("cantidad_registros", ascending=[False]).head(15)
    can_registros_grafico = can_registros_grafico.set_index('nombre_can')  

    with col1:
        st.header('Cantidad de registros por can')

        fig = px.bar(can_registros_grafico, 
                    labels={'nombre_can':'can', 'cantidad_registros':'Registros de presencia'})
        st.plotly_chart(fig)    

    with col2:        
        # st.subheader('px.pie()')        
        st.header('Porcentaje de registros por can')
        
        fig = px.pie(can_registros_grafico, 
                    names=can_registros_grafico.index,
                    values='cantidad_registros')
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig)    


    with col1:
        # Mapa de calor y de registros agrupados
        st.header('Mapa de calor y de registros agrupados')

        # Capa base
        m = folium.Map(location=[9.6, -84.2], tiles='CartoDB dark_matter', zoom_start=8)
        # Capa de calor
        HeatMap(data=registros[['decimalLatitude', 'decimalLongitude']],
                name='Mapa de calor').add_to(m)
        # Capa de can
        folium.GeoJson(data=can, name='can').add_to(m)
        # Capa de registros de presencia agrupados
        mc = MarkerCluster(name='Registros agrupados')
        for idx, row in registros.iterrows():
            if not math.isnan(row['decimalLongitude']) and not math.isnan(row['decimalLatitude']):
                mc.add_child(Marker([row['decimalLatitude'], row['decimalLongitude']], 
                                    popup=row['species']))
        m.add_child(mc)
        # Control de capas
        folium.LayerControl().add_to(m)    
        # Despliegue del mapa
        folium_static(m)

    with col2:
        # Mapa de coropletas de registros de presencia en can
        st.header('Mapa de cantidad de registros en can')

        # Capa base
        m = folium.Map(location=[9.6, -84.2], tiles='CartoDB positron', zoom_start=8)
        # Capa de coropletas
        folium.Choropleth(
            name="Cantidad de registros en can",
            geo_data=can,
            data=can_registros,
            columns=['cod_canton', 'cantidad_registros'],
            bins=8,
            key_on='feature.properties.cod_canton',
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
    st.map(registros.rename(columns = {'decimalLongitude':'longitude', 'decimalLatitude':'latitude'}))

    '''
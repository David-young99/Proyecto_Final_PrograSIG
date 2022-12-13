# Aplicación desarrollada en Streamlit para visualización de datos de biodiversidad
# Autor: Manuel Vargas (mfvargas@gmail.com)
# Fecha de creación: 2022-11-19
# El código original fue adaptado por los estudiantes: Alexandra Salazar y David Young

#Version:5.2.1  =   commit 


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
datos_usuarios = st.sidebar.file_uploader('Seleccione un archivo CSV que siga el estándar DwC')

# Procesamiento de datos, solo si hay un archivo de datos cargado
if datos_usuarios is not None:
    # Carga de registros de presencia en un dataframe con nombre de "registros"
    registros = pd.read_csv(datos_usuarios, delimiter='\t')
    # Conversión del dataframe de registros de presencia a geodataframe, identifica en código las columnas de las coordenadas
    registros = gpd.GeoDataFrame(registros, 
                                           geometry=gpd.points_from_xy(registros.decimalLongitude, 
                                                                       registros.decimalLatitude),
                                           crs='EPSG:4326')


    # Carga de poligonos: capa cantones
    can = gpd.read_file("datos/cantones/cantones.geojson")

    can_prov = gpd.read_file("datos/cantones/cantones.geojson")



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

    # Cálculo de la cantidad de registros por cantón
    # "Join" espacial de las capas de cantones y registros de presencia de especies
    can_contienen_registros = can.sjoin(registros, how="left", predicate="contains")
    # Conteo de registros de presencia por cada cantón
    can_registros_prov = can_contienen_registros.groupby("CODNUM").agg(cantidad_registros_presencia = ("gbifID","count"))
    can_registros_prov = can_registros_prov.reset_index() # para convertir la serie a dataframe


    #Cálculo de la cantidad de registros por provincia
    prov_contienen_registros = can_prov.sjoin(registros, how="left", predicate="contains")
    # "Join" espacial de las capas de cantones (atributo provincia) y registros de presencia de especies registradas
    prov_registros = prov_contienen_registros.groupby("PROV").agg(cantidad_registros_presencia_prov = ("gbifID","count"))
    prov_registros = prov_registros.reset_index() # para convertir la serie a dataframe
    


    #
    # SALIDAS ------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #

    # Tabla de registros de presencia (modifica la primer tabla que se muestra en la aplicación web)
    st.header('Registros de presencia de especies')
    st.dataframe(registros[['species', 'stateProvince', 'locality','eventDate']].rename(columns = {'species':'Especie', 'stateProvince':'Provincia', 'locality':'Localidad', 'eventDate':'Fecha'}),width=1300)


    # Definición de columnas de la parte visual de nuestra aplicación, dividará el contenido en dos columnas
    col1, col2 = st.columns(2)



    

   

    # Conteo de cantidad de registros de presencia por cantón **Para el gráfico**
    # "Join" para agregar la columna con el conteo a la capa de provincia
    can_registros_prov = can_registros_prov.join(can.set_index('CODNUM'), on='CODNUM', rsuffix='_b')
    # Dataframe filtrado para usar en graficación
    can_registros_grafico_prov = can_registros_prov.loc[can_registros_prov['cantidad_registros_presencia'] > 0, 
                                                            ["provincia", "cantidad_registros_presencia"]].sort_values("cantidad_registros_presencia")
    can_registros_grafico_prov = can_registros_grafico_prov.set_index('provincia') 



    with col1:
        # Gráficos de historial de registros de presencia por provincia
        st.header('Historial de registros por provincia')

        fig = px.bar(can_registros_grafico_prov, 
                    labels={'provincia':'Provincia', 'cantidad_registros_presencia_prov':'Registros de presencia'})    

        fig.update_layout(barmode='stack', xaxis={'categoryorder': 'total descending'})
        st.plotly_chart(fig)    
 


     # Gráficos de cantidad de registros de presencia por cantón
    # "Join" para agregar la columna con el conteo a la capa de cantón
    can_registros_prov = can_registros_prov.join(can.set_index('CODNUM'), on='CODNUM', rsuffix='_b')
    # Dataframe filtrado para usar en graficación
    can_registros_grafico_prov = can_registros_prov.loc[can_registros_prov['cantidad_registros_presencia'] > 0, 
                                                            ["NCANTON", "cantidad_registros_presencia"]].sort_values("cantidad_registros_presencia")
    can_registros_grafico_prov = can_registros_grafico_prov.set_index('NCANTON')  
    

    with col2:
        # Gráficos de historial de registros de presencia por cantón
        st.header('Historial de registros por cantón')

        fig = px.bar(can_registros_grafico_prov, 
                    labels={'NCANTON':'Cantón', 'cantidad_registros_presencia':'a'})    

        fig.update_layout(barmode='stack', xaxis={'categoryorder': 'total descending'})
        st.plotly_chart(fig)


    # Mapas de coropletas
    st.header('Mapa de registros de presencia de especies por provincia, cantón y agrupados')

    # Capa base
    m = folium.Map(
    location=[9.73333, -84],
    tiles='CartoDB positron', 
    zoom_start=7.5,
    control_scale=True)


    # Se añaden capas base adicionales
    folium.TileLayer(
    tiles='CartoDB dark_matter', 
    name='CartoDB dark matter').add_to(m)


    # Capa de coropletas para clasifición cantonal
    can_map = folium.Choropleth(
        name="Mapa de coropletas de los registros por cantón",
        geo_data=can,
        data=can_registros_prov,
        columns=['CODNUM', 'cantidad_registros_presencia'],
        bins=8,
        key_on='feature.properties.CODNUM',
        fill_color='PuBuGn', 
        fill_opacity=0.5, 
        line_opacity=1,
        legend_name='Cantidad de registros de presencia por cantón',
        smooth_factor=0).add_to(m)
        
    folium.GeoJsonTooltip(['NCANTON', 'provincia']).add_to(can_map.geojson)


    # Conteo de cantidad de registros de presencia por provincia **para cartografía coroplética**
    # "Join" para agregar la columna con el conteo a la capa de provincia,OJO, este nuevo join es únicamente para el mapa
    prov_registros = prov_registros.join(can_prov.set_index('PROV'), on='PROV', rsuffix='_b')
    # Dataframe filtrado para usar en graficación
    prov_registros_grafico = prov_registros.loc[prov_registros['cantidad_registros_presencia_prov'] > 0, 
                                                            ["provincia", "cantidad_registros_presencia_prov"]].sort_values("cantidad_registros_presencia_prov")
    prov_registros_grafico = prov_registros_grafico.set_index('provincia')  


    # Capa de coropletas para clasifición provincial
    prov_map = folium.Choropleth(
        name="Mapa de coropletas de los registros por provincia",
        geo_data=can_prov,
        data=prov_registros,
        columns=['provincia', 'cantidad_registros_presencia_prov'],
        bins=5,
        key_on='feature.properties.provincia',
        fill_color='PuBuGn', 
        fill_opacity=0.5, 
        line_opacity=1,
        legend_name='Cantidad de registros de presencia por provincia',
        smooth_factor=0).add_to(m)

    folium.GeoJsonTooltip(['NCANTON', 'provincia']).add_to(prov_map.geojson)


    # Capa de registros de presencia agrupados
    mc = MarkerCluster(name='Registros agrupados cantonal')
    for idx, row in registros.iterrows():
        if not math.isnan(row['decimalLongitude']) and not math.isnan(row['decimalLatitude']):
            mc.add_child(
                Marker([row['decimalLatitude'], row['decimalLongitude'], ], 
                                popup= "--Nombre de la especie: " + str(row["species"]) + "\n" + " --Provincia: " + str(row["stateProvince"]) + "\n" + "--Fecha: " + str(row["eventDate"]),
                                icon=folium.Icon(color="green")))
    m.add_child(mc)

    

    # Control de capas
    folium.LayerControl().add_to(m) 
    # Despliegue del mapa
    folium_static(m, width=1300, height=625)
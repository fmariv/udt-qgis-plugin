# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the MunicipalMap class is defined. The main function
of this class is to run the automation process that edits a Municipal map layout,
in order to automatically add some information related to the document and the municipi
and make the layout editable for the user.
***************************************************************************/
"""

import numpy as np
import os

from qgis.core import (QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem,
                       QgsField,
                       QgsFeature,
                       QgsGeometry,
                       QgsProject,
                       QgsMessageLog,
                       QgsWkbTypes,
                       QgsFillSymbol,
                       QgsLayoutExporter,
                       QgsProcessingFeedback,
                       QgsRasterLayer)
import processing

from ..config import *
from ..utils import *
from .adt_postgis_connection import PgADTConnection

# TODO reordenar carpeta

# 212


class MunicipalMap:
    """ Municipal map generation class """

    def __init__(self, municipi_id, input_directory, layout_size, iface, hillshade):
        # Initialize instance attributes
        # Set environment variables
        self.municipi_id = municipi_id
        self.input_directory = input_directory
        self.layout_size = layout_size
        self.iface = iface
        self.hillshade = hillshade
        # Common
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        self.rec_table = self.pg_adt.get_table('reconeixement')
        self.dogc_table = self.pg_adt.get_table('pa_pub_dogc')
        self.mtt_table = self.pg_adt.get_table('memoria_treb_top')
        self.project = QgsProject.instance()
        self.arr_municipi_data = np.genfromtxt(LAYOUT_MUNI_DATA, dtype=None, encoding='utf-8-sig', delimiter=';', names=True)
        self.arr_lines_data = np.genfromtxt(LAYOUT_LINE_DATA, dtype=None, encoding='utf-8-sig', delimiter=';', names=True)
        self.layout_manager = self.project.layoutManager()
        # Input dependant
        # Paths
        self.set_directories_paths()
        if self.hillshade:
            self.hillshade_txt_path = os.path.join(self.input_directory, 'ombra.txt')
        # Layers
        self.set_layers()
        self.municipi_name = self.get_municipi_name()
        self.act_rec_exists = False
        self.pub_dogc_exits = False
        # Layer dependant
        self.municipi_sup = self.get_municipi_sup()
        self.municipi_lines = self.get_municipi_lines()
        self.rec_text = self.get_rec_dogc_text()
        self.mtt_text = self.get_mtt_text()
        # The layout size determines the layout to generate
        self.layout_name = self.get_layout_name()
        self.layout = self.layout_manager.layoutByName(self.layout_name)

    # #######################
    # Setters & Getters
    def get_layout_name(self):
        """  """
        return SIZE[self.layout_size]

    def get_municipi_name(self):
        """  """
        data = np.where(self.arr_municipi_data['id_area'] == f'"{self.municipi_id}"')
        index = data[0][0]
        muni_data = self.arr_municipi_data[index]
        muni_name = muni_data[1]

        return muni_name

    def get_municipi_sup(self):
        """  """
        sup = None
        for polygon in self.polygon_layer.getFeatures():
            sup = polygon['Sup_CDT']
            break

        return sup

    def get_municipi_lines(self):
        """ Get all the municipal boundary lines that make the input municipi """
        line_list = []
        for line in self.lines_layer.getFeatures():
            line_id = line['id_linia']
            line_list.append(int(line_id))

        return line_list

    def get_rec_dogc_text(self):
        """  """
        rec_text_list = []
        for line_id in self.municipi_lines:
            self.rec_table.selectByExpression(f'"id_linia"={line_id} and "vig_act_rec" is True')

            for rec in self.rec_table.getSelectedFeatures():
                text = ''
                rec_date = rec['data_act_rec']
                if isinstance(rec['obs_act_rec'], str):
                    if 'DOGC' not in rec['obs_act_rec']:
                        self.act_rec_exists = True
                        text = self.get_rec_text(line_id, rec_date)
                    else:
                        self.pub_dogc_exits = True
                        text = self.get_dogc_text(line_id, rec_date)
                else:
                    if 'DOGC' not in str(rec['obs_act_rec'].value()):
                        self.act_rec_exists = True
                        text = self.get_rec_text(line_id, rec_date)
                    else:
                        self.pub_dogc_exits = True
                        text = self.get_dogc_text(line_id, rec_date)
                rec_text_list.append(text)

        return rec_text_list

    def get_rec_text(self, line_id, date):
        """  """
        muni_1_nomens, muni_2_nomens = self.get_municipis_nomens(line_id)
        string_date = self.get_string_date(date)
        rec_text = f'Acta de reconeixement de la línia de terme i assenyalament de les fites comunes dels termes ' \
                   f'municipals {muni_1_nomens} i {muni_2_nomens}, de {string_date}.\n'

        return rec_text

    def get_dogc_text(self, line_id, date):
        """  """
        date_ = date.toString("yyyy-MM-dd")
        self.dogc_table.selectByExpression(f'"id_linia"={line_id} AND "vig_pub_dogc" is True AND '
                                           f'"data_doc"=\'{date_}\'')   # tip_pub_dogc = 2 -> Correcció d'errades
        text = ''
        for dogc in self.dogc_table.getSelectedFeatures():
            title = dogc['tit_pub_dogc']
            text = normalize_dogc_title(title)
            break

        return text

    def get_mtt_text(self):
        """  """
        mtt_text_list = []
        for line_id in self.municipi_lines:
            muni_1_nomens, muni_2_nomens = self.get_municipis_nomens(line_id)
            self.mtt_table.selectByExpression(f'"id_linia" = {line_id} AND "vig_mtt" is True')

            for mtt in self.mtt_table.getSelectedFeatures():
                date = mtt['data_doc']
                string_date = self.get_string_date(date)
                mtt_text = f'Memòria dels treballs topogràfics de la línia de delimitació entre els' \
                           f' termes municipals {muni_1_nomens} i {muni_2_nomens}, de {string_date}.\n'
                mtt_text_list.append(mtt_text)
                break

        return mtt_text_list

    def get_municipis_nomens(self, line_id):
        """
        Get the way to name the municipis
        :return: muni_1_nomens - Way to name the first municipi
        :return: muni_2_nomens - Way to name the second municipi
        """
        muni_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)][0]
        muni_1_nomens = muni_data[3]
        muni_2_nomens = muni_data[4]

        return muni_1_nomens, muni_2_nomens

    @staticmethod
    def get_string_date(date):
        """
        Get the current date as a string
        :return: string_date - Current date as string, with format [day month year]
        """
        date = date.toString("yyyy-MM-dd")
        date_splitted = date.split('-')
        day = date_splitted[-1]
        if day[0] == '0':
            day = day[1]
        year = date_splitted[0]
        month = MESOS_CAT[date_splitted[1]]
        string_date = f'{day} {month} {year}'

        return string_date

    def set_directories_paths(self):
        """  """
        self.shapes_dir = os.path.join(self.input_directory, 'ESRI/Shapefiles')
        self.dgn_dir = os.path.join(self.input_directory, 'ESRI/DGN')
        self.dxf_dir = os.path.join(self.input_directory, 'ESRI/DXF')

    def set_layers(self):
        """  """
        self.lines_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Linies.shp'), 'MM_Linies')
        self.points_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Fites.shp'), 'MM_Fites')
        self.polygon_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Poligons.shp'), 'MM_Poligons')
        self.neighbor_lines_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Lveines.shp'), 'MM_Lveines')
        self.neighbor_polygons_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Municipisveins.shp'), 'MM_Municipisveins')
        self.place_name_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'Nuclis.shp'), 'Nuclis')

        self.map_layers = [self.polygon_layer, self.neighbor_lines_layer, self.lines_layer, self.place_name_layer,
                           self.points_layer, self.neighbor_polygons_layer]

    # #######################
    # Generate the Municipal map layout
    def generate_municipal_map(self):
        """  """
        if self.hillshade:
            self.generate_hillshade()
        self.remove_map_layers()
        self.add_map_layers()
        self.add_layers_styles()
        self.edit_municipi_name_label()
        self.edit_municipi_sup_label()
        self.edit_rec_title_label()
        self.edit_rec_item_label()
        self.edit_mtt_item_label()
        self.zoom_to_polygon_layer()

    def zoom_to_polygon_layer(self):
        """"  """
        # The plugin only zooms correctly if previously exist layers in the map canvas
        self.polygon_layer.selectAll()
        self.iface.mapCanvas().zoomToSelected(self.polygon_layer)
        self.iface.mapCanvas().refresh()
        self.polygon_layer.removeSelection()

    def add_map_layers(self):
        """  """
        for layer in self.map_layers:
            self.project.addMapLayer(layer)

    def remove_map_layers(self):
        """  """
        layers = self.project.mapLayers().values()
        if layers:
            QgsProject.instance().removeAllMapLayers()

    def add_layers_styles(self):
        """  """
        layers = self.project.mapLayers().values()
        for layer in layers:
            if layer.name() == 'MM_Poligons':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'poligon.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Fites':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'fites.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Lveines':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'linies_veines.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Linies':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'linies.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Municipisveins':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'etiquetes_municipi_veins.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'Nuclis':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'nuclis.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'Ombra':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'ombra.qml'))
                layer.triggerRepaint()

    # ###########
    # Edit layout labels
    def edit_municipi_name_label(self):
        """  """
        municipi_name_item = self.layout.itemById('Municipi')
        municipi_name_item.setText(self.municipi_name)

    def edit_municipi_sup_label(self):
        """  """
        municipi_name_item = self.layout.itemById('Sup_CDT')
        municipi_name_item.setText(f'Superfície municipal: {str(self.municipi_sup)} km')

    def edit_rec_title_label(self):
        """  """
        text = "Relació d'actes de reconeixement i resolucions publicades al DOGC vigents:"   # Default text
        rec_title_item = self.layout.itemById('Actes_rec_title')
        if self.act_rec_exists and not self.pub_dogc_exits:
            text = "Relació d'actes de reconeixement vigents:"
        elif self.act_rec_exists and self.pub_dogc_exits:
            text = "Relació d'actes de reconeixement i resolucions publicades al DOGC vigents:"
        elif not self.act_rec_exists and self.pub_dogc_exits:
            text = "Relació de resolucions publicades al DOGC vigents:"

        rec_title_item.setText(text)

    def edit_rec_item_label(self):
        """  """
        rec_item = self.layout.itemById('Actes_rec_items')
        text = ''.join(self.rec_text)
        rec_item.setText(text)

    def edit_mtt_item_label(self):
        """  """
        mtt_item = self.layout.itemById('MTT_items')
        text = ''.join(self.mtt_text)
        mtt_item.setText(text)

    # #######################
    # Generate the hillshade
    def generate_hillshade(self):
        """  """
        translated_raster = self.translate_raster()
        self.hillshade_raster(translated_raster)

    def translate_raster(self):
        """  """
        municipi_raster = QgsRasterLayer(self.hillshade_txt_path)
        output = os.path.join(TEMP_DIR, f'translate_{self.municipi_id}.tif')
        translate_parameters = {'INPUT': municipi_raster, 'TARGET_CRS': 'EPSG:25831',
                                'OUTPUT': output}
        processing.run('gdal:translate', translate_parameters)

        translated_raster = QgsRasterLayer(output)
        return translated_raster

    def hillshade_raster(self, translated_raster):
        """  """
        output = os.path.join(self.input_directory, 'ombra.tif')
        hillshade_parameters = {'INPUT': translated_raster, 'BAND': 1, 'Z_FACTOR': 3,
                                'OUTPUT': output}
        processing.run('gdal:hillshade', hillshade_parameters)

        hillshade_raster = QgsRasterLayer(output, 'Ombra')
        # Edit the layer's list and append the hillshade raster as the first item, in order to see it as the
        # map base
        self.map_layers.insert(0, hillshade_raster)

    def check_hillshade_txt_exits(self):
        """  """
        if not os.path.exists(self.hillshade_txt_path):
            return False
        else:
            return True

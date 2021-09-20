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
import shutil

from qgis.core import (QgsVectorLayer,
                       QgsProject,
                       QgsMessageLog,
                       QgsRasterLayer)
import processing

from ..config import *
from ..utils import *
from .adt_postgis_connection import PgADTConnection

# TODO las capas del canvas no son las de la nueva carpeta, si no las de la antigua. Por eso no se puede
#  eliminar la antigua hasta generar el pdf


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
        self.municipi_name, self.municipi_nomens = self.get_municipi_name()
        self.act_rec_exists = False
        self.pub_dogc_exits = False
        # Layer dependant
        self.municipi_sup = self.get_municipi_sup()
        self.municipi_lines = self.get_municipi_lines()
        self.mtt_dates = {}
        self.rec_text = self.get_rec_dogc_text()
        self.mtt_text = self.get_mtt_text()
        # The layout size determines the layout to generate
        self.layout_name = self.get_layout_name()
        self.layout = self.layout_manager.layoutByName(self.layout_name)

    # #######################
    # Setters & Getters
    def get_layout_name(self):
        """
        Get the layout name depending on the user's size input
        :return: QGIS project's layout name
        """
        return SIZE[self.layout_size]

    def get_municipi_name(self):
        """
        Get the municipi name depending on the user's municipi ID input
        :return: muni_name - Name of the municipi
        :return: muni_nomens - Nomens of the municipi
        """
        data = np.where(self.arr_municipi_data['id_area'] == f'"{self.municipi_id}"')
        index = data[0][0]
        muni_data = self.arr_municipi_data[index]
        muni_name = muni_data[1]
        muni_nomens = muni_data[5]

        return muni_name, muni_nomens

    def get_municipi_sup(self):
        """
        Get the municipi polygon area
        :return: sup - Municipal's polygon area
        """
        sup = None
        for polygon in self.polygon_layer.getFeatures():
            sup = polygon['Sup_CDT']
            break

        return sup

    def get_municipi_lines(self):
        """
        Get all the municipal boundary lines that make the input municipi
        :return: line list - List of the municipi's boundary lines
        """
        line_list = []
        for line in self.lines_layer.getFeatures():
            line_id = line['id_linia']
            line_list.append(int(line_id))

        return line_list

    def get_rec_dogc_text(self):
        """
        Get the title of the DOGC publication or acta de reconeixement of every municipi's boundary line, in order
        to write them later in the layout. First of all, the function checks if the line has a DOGC publication
        or acta de reconeixement.
        :return: rec_text_list - List with the title of whether the DOGC titles or Acta de reconeixement titles
                                 of every line
        """
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
        """
        Get the title of the acta de reconeixement of the boundary line
        :return: rec_text - Title of the line's Acta de reconeixement
        """
        muni_1_nomens, muni_2_nomens = self.get_municipis_nomens(line_id)
        string_date = self.get_string_date(date)
        rec_text = f'Acta de reconeixement de la línia de terme i assenyalament de les fites comunes dels termes ' \
                   f'municipals {muni_1_nomens} i {muni_2_nomens}, de {string_date}.\n'

        return rec_text

    def get_dogc_text(self, line_id, date):
        """
        Get the title of the DOGC publication of the boundary line
        :return: dogc_text - Title of the line's DOGC publication
        """
        date_ = date.toString("yyyy-MM-dd")
        self.dogc_table.selectByExpression(f'"id_linia"={line_id} AND "vig_pub_dogc" is True AND '
                                           f'"data_doc"=\'{date_}\' AND "tip_pub_dogc" != 2')   # tip_pub_dogc = 2 -> Correcció d'errades, que no poden sortir al document
        dogc_text = ''
        for dogc in self.dogc_table.getSelectedFeatures():
            title = dogc['tit_pub_dogc']
            dogc_text = normalize_dogc_title(title)
            break

        return dogc_text

    def get_mtt_text(self):
        """
        Get the title of the MTT of the boundary line
        :return: mtt_text_list - List of the municipal's boundary lines MTT's titles
        """
        mtt_text_list = []
        for line_id in self.municipi_lines:
            muni_1_nomens, muni_2_nomens = self.get_municipis_nomens(line_id)
            self.mtt_table.selectByExpression(f'"id_linia" = {line_id} AND "vig_mtt" is True')

            for mtt in self.mtt_table.getSelectedFeatures():
                date = mtt['data_doc']
                self.mtt_dates[line_id] = date.toString("yyyyMMdd")   # Add to the MTT dates dict, will be used later
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
        """ Set the data directories paths """
        self.shapes_dir = os.path.join(self.input_directory, 'ESRI/Shapefiles')
        self.dgn_dir = os.path.join(self.input_directory, 'ESRI/DGN')
        self.dxf_dir = os.path.join(self.input_directory, 'ESRI/DXF')

    def set_layers(self):
        """ Set the QGIS Vector Layers """
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
        """ Entry point for generating the input Municipal's map layout """
        if self.hillshade:
            self.generate_hillshade()
        # Set the layout
        self.remove_map_layers()
        self.add_map_layers()
        self.add_layers_styles()
        self.zoom_to_polygon_layer()
        # Edit the layout
        self.edit_municipi_name_label()
        self.edit_municipi_sup_label()
        self.edit_rec_title_label()
        self.edit_rec_item_label()
        self.edit_mtt_item_label()
        # Create the new directory
        self.create_new_directory()

    def zoom_to_polygon_layer(self):
        """" Zoom the map canvas to the polygon layer """
        # The plugin only zooms correctly if previously exist layers in the map canvas
        self.polygon_layer.selectAll()
        self.iface.mapCanvas().zoomToSelected(self.polygon_layer)
        self.iface.mapCanvas().refresh()
        self.polygon_layer.removeSelection()

    def add_map_layers(self):
        """ Add the municipal map layers to the canvas """
        for layer in self.map_layers:
            self.project.addMapLayer(layer)

    def remove_map_layers(self):
        """ Remove the previous municipal map layers of the canvas """
        layers = self.project.mapLayers().values()
        if layers:
            QgsProject.instance().removeAllMapLayers()

    def add_layers_styles(self):
        """ Add style to the newly added layers """
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
        """ Edit the layout's municipal name label """
        municipi_name_item = self.layout.itemById('Municipi')
        municipi_name_item.setText(self.municipi_name)

    def edit_municipi_sup_label(self):
        """ Edit the layout's municipal area label """
        municipi_name_item = self.layout.itemById('Sup_CDT')
        municipi_name_item.setText(f'Superfície municipal: {str(self.municipi_sup)} km')

    def edit_rec_title_label(self):
        """
        Edit the Reconeixement title, depending on whether the municipal's boundary lines only have DOGC publication,
        actes de reconeixement or both categories
        """
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
        """ Add the titles of both municipal's boundary lines DOGC publications and Actes de reconeixement """
        rec_item = self.layout.itemById('Actes_rec_items')
        text = ''.join(self.rec_text)
        rec_item.setText(text)

    def edit_mtt_item_label(self):
        """ Add the titles of the municipal's boundary lines MTT """
        mtt_item = self.layout.itemById('MTT_items')
        text = ''.join(self.mtt_text)
        mtt_item.setText(text)

    # #######################
    # Generate the hillshade
    def generate_hillshade(self):
        """ Entry point for the hillshade generation """
        translated_raster = self.translate_raster()
        self.hillshade_raster(translated_raster)

    def translate_raster(self):
        """ Translate the input raster txt file, in order to reproject it and save as a .tif file format """
        municipi_raster = QgsRasterLayer(self.hillshade_txt_path)
        output = os.path.join(TEMP_DIR, f'translate_{self.municipi_id}.tif')
        translate_parameters = {'INPUT': municipi_raster, 'TARGET_CRS': 'EPSG:25831',
                                'OUTPUT': output}
        processing.run('gdal:translate', translate_parameters)

        translated_raster = QgsRasterLayer(output)
        return translated_raster

    def hillshade_raster(self, translated_raster):
        """ Generate the hillshade from the translated input raster """
        output = os.path.join(self.input_directory, 'ombra.tif')
        hillshade_parameters = {'INPUT': translated_raster, 'BAND': 1, 'Z_FACTOR': 3,
                                'OUTPUT': output}
        processing.run('gdal:hillshade', hillshade_parameters)

        hillshade_raster = QgsRasterLayer(output, 'Ombra')
        # Edit the layer's list and append the hillshade raster as the first item, in order to see it as the
        # map base
        self.map_layers.insert(0, hillshade_raster)

    def check_hillshade_txt_exits(self):
        """ Check if the input raster txt file exists """
        if not os.path.exists(self.hillshade_txt_path):
            return False
        else:
            return True

    # #######################
    # New municipal map directory
    def create_new_directory(self):
        """ Entry point for the new directory generation """
        # Create new main directory
        normalized_municipi_name = self.municipi_name.replace("'", "").replace(" ", "-")
        name = f'MM_{normalized_municipi_name}'
        new_main_directory = self.input_directory.replace(self.input_directory.split("\\")[-1], name)
        os.mkdir(new_main_directory)
        # Add sub directories
        self.add_sub_directories(new_main_directory)
        # Copy files
        self.copy_files(new_main_directory)
        # Create txt
        self.create_txt(new_main_directory, name)
        # Copy MTT
        self.copy_mtt(new_main_directory)

    @staticmethod
    def add_sub_directories(new_main_directory):
        """ Add the pertinent sub directories to the new main directory """
        for dir_ in ('Autocad', 'ESRI', 'Memòries_topogràfiques', 'Microstation'):
            os.mkdir(os.path.join(new_main_directory, dir_))
        # Add sub directories to the ESRI directory
        for dir__ in ('layer_propietats', 'Shapefiles'):
            os.mkdir(os.path.join(new_main_directory, 'ESRI', dir__))

    def copy_files(self, new_main_directory):
        """ Copy all the necessary files to the new directory """
        # Microstation
        for dgn in os.listdir(self.dgn_dir):
            if 'Nuclis' not in dgn and 'MM_Lveines' not in dgn and 'MM_Municipisveins' not in dgn:
                shutil.copy(os.path.join(self.dgn_dir, dgn), os.path.join(new_main_directory, 'Microstation', dgn))
        # AutoCAD
        for cad in os.listdir(self.dxf_dir):
            if 'Nuclis' not in cad and 'MM_Lveines' not in cad and 'MM_Municipisveins' not in cad:
                shutil.copy(os.path.join(self.dxf_dir, cad), os.path.join(new_main_directory, 'Autocad', cad))
        # Shapefiles
        for shape in os.listdir(self.shapes_dir):
            shutil.copy(os.path.join(self.shapes_dir, shape),
                        os.path.join(new_main_directory, 'ESRI/Shapefiles', shape))
        # Hillshade
        hillshade_path = os.path.join(self.input_directory, 'ombra.tif')
        if os.path.exists(hillshade_path):
            shutil.copy(hillshade_path, os.path.join(new_main_directory, 'ESRI', 'ombra.tif'))
        # Styles
        for qml in os.listdir(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR):
            shutil.copy(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, qml),
                        os.path.join(new_main_directory, 'ESRI/layer_propietats', qml))

    def create_txt(self, new_main_directory, name):
        """ Create a info txt file for in new directory """
        with open(os.path.join(new_main_directory, f'{name}.txt'), 'a+') as f:
            f.write('MAPA MUNICIPAL DE CATAlUNYA\n\n')
            f.write(f'Terme municipal {self.municipi_nomens}.\n\n')
            f.write('Sotmès a la consideració de la Comissió de Delimitació Territorial en la seva sessió de <data>.')

    def copy_mtt(self, new_main_directory):
        """ Copy the municipal's boundary lines MTT files in the new directory """
        for line_id in self.municipi_lines:
            line = str(line_id)
            line_txt = line_id_2_txt(line)   # Line ID in NNNN format
            mtt_date = self.mtt_dates[line_id]
            line_mtt_dir = os.path.join(LINES_DIR, line, MTT_DIR)

            for mtt in os.listdir(line_mtt_dir):
                if mtt.startswith(f'MTT_{line_txt}_{mtt_date}_'):
                    shutil.copy(os.path.join(line_mtt_dir, mtt), os.path.join(new_main_directory,
                                                                              'Memòries_topogràfiques', mtt))

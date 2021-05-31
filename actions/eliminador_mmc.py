# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the EliminadorMMC class is defined. The main function
of this class is to run the automation process that removes a municipal
map and all of its features from the latest layer of the Municipal Map of Catalonia.
***************************************************************************/
"""

import os
import numpy as np

from qgis.core import (QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem,
                       QgsField,
                       QgsFeature,
                       QgsGeometry,
                       QgsProject)
from qgis.core.additions.edit import edit
from PyQt5.QtWidgets import QMessageBox

from ..config import *
from ..utils import *
from .adt_postgis_connection import PgADTConnection


class EliminadorMMC:
    """ MMC Deletion class """

    def __init__(self, municipi_id, coast=False):
        # Common
        self.arr_nom_municipis = np.genfromtxt(DIC_NOM_MUNICIPIS, dtype=None, encoding=None, delimiter=';', names=True)
        self.arr_lines_data = np.genfromtxt(DIC_LINES, dtype=None, encoding=None, delimiter=';', names=True)
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        # ###
        # Input dependant that don't need data from the layers
        self.municipi_id = int(municipi_id)
        self.coast = coast
        self.municipi_codi_ine = self.get_municipi_codi_ine(self.municipi_id)
        self.municipi_lines = self.get_municipi_lines()   # Get a list with all the lines ID
        if self.coast:
            self.municipi_coast_line = self.get_municipi_coast_line()
        # Input layers
        self.input_points_layer, self.input_lines_layer, self.input_polygons_layer, self.input_coast_lines_layer, self.input_full_bt5_table, self.input_line_table, self.input_coast_line_table = (None,) * 7

    def get_municipi_codi_ine(self, municipi_id):
        """  """
        muni_data = self.arr_nom_municipis[np.where(self.arr_nom_municipis['id_area'] == f'"{municipi_id}"')]
        codi_ine = muni_data['codi_ine_muni'][0].strip('"\'')

        return codi_ine

    def get_municipi_lines(self):
        """  """
        lines_muni_1 = self.arr_lines_data[np.where(self.arr_lines_data['CODIMUNI1'] == self.municipi_id)]
        lines_muni_2 = self.arr_lines_data[np.where(self.arr_lines_data['CODIMUNI2'] == self.municipi_id)]
        lines_muni_1_list = lines_muni_1['IDLINIA'].tolist()
        lines_muni_2_list = lines_muni_2['IDLINIA'].tolist()

        lines_muni_list = lines_muni_1_list + lines_muni_2_list

        return lines_muni_list

    def check_mm_exists(self, municipi_codi_ine):
        """  """
        mapa_muni_table = self.pg_adt.get_table('mapa_muni_icc')
        # todo que se pueda elegir buscar en postgis o en la capa de polígonos
        mapa_muni_table.selectByExpression(f'"codi_muni"=\'{municipi_codi_ine}\' and "vig_mm" is True',
                                           QgsVectorLayer.SetSelection)
        count = mapa_muni_table.selectedFeatureCount()
        if count == 0:
            return False
        else:
            return True

    def get_municipi_coast_line(self):
        """ Get the municipi coast line, if exists """
        coast_line_id = ''
        for line_id in self.municipi_lines:
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]
            if line_data['LIMCOSTA'] == 'S':
                coast_line_id = line_id

        return coast_line_id

    def remove_municipi_data(self):
        """  """
        self.set_layers()
        self.remove_polygons()
        if self.coast:
            self.remove_coast_line()
            self.remove_full_bt5m()

    def set_layers(self):
        """  """
        directory_list = os.listdir(ELIMINADOR_INPUT_DIR)
        directory_path = os.path.join(ELIMINADOR_INPUT_DIR, directory_list[0])
        shapefiles_list = os.listdir(directory_path)

        for shapefile in shapefiles_list:
            if '-fita-' in shapefile and shapefile.endswith('.shp'):
                self.input_points_layer = QgsVectorLayer(os.path.join(directory_path, shapefile))
            if '-liniaterme-' in shapefile and shapefile.endswith('.shp'):
                self.input_lines_layer = QgsVectorLayer(os.path.join(directory_path, shapefile))
            if '-poligon-' in shapefile and shapefile.endswith('.shp'):
                self.input_polygons_layer = QgsVectorLayer(os.path.join(directory_path, shapefile))
            if '-liniacosta-' in shapefile and shapefile.endswith('.shp'):
                self.input_coast_lines_layer = QgsVectorLayer(os.path.join(directory_path, shapefile))
            if '-liniacostataula-' in shapefile and shapefile.endswith('.dbf'):
                self.input_coast_line_table = QgsVectorLayer(os.path.join(directory_path, shapefile))
            if '-tallfullbt5m-' in shapefile and shapefile.endswith('.dbf'):
                self.input_full_bt5_table = QgsVectorLayer(os.path.join(directory_path, shapefile))
            if '-liniatermetaula-' in shapefile and shapefile.endswith('.dbf'):
                self.input_line_table = QgsVectorLayer(os.path.join(directory_path, shapefile))

    def remove_polygons(self):
        """  """
        self.input_polygons_layer.selectByExpression(f'"CodiMuni"=\'{self.municipi_codi_ine}\'',
                                                     QgsVectorLayer.SetSelection)
        with edit(self.input_polygons_layer):
            for polygon in self.input_polygons_layer.getSelectedFeatures():
                self.input_polygons_layer.deleteFeature(polygon.id())

    def remove_coast_line(self):
        """  """
        self.input_coast_lines_layer.selectByExpression(f'"IdLinia"={self.municipi_coast_line}',
                                                        QgsVectorLayer.SetSelection)
        with edit(self.input_coast_lines_layer):
            for line in self.input_coast_lines_layer.getSelectedFeatures():
                self.input_coast_lines_layer.deleteFeature(line.id())

    def remove_full_bt5m(self):
        """  """
        # TODO testear
        self.input_full_bt5_table.selectByExpression(f'"IdLinia"={self.municipi_coast_line}',
                                                     QgsVectorLayer.SetSelection)
        with edit(self.input_full_bt5_table):
            for line in self.input_full_bt5_table.getSelectedFeatures():
                self.input_full_bt5_table.deleteFeature(line.id())

    def remove_points(self):
        """  """
        fita_mem_layer = self.pg_adt.get_layer('v_fita_mem', 'id_fita')
        point_id_list = []
        for line_id in self.municipi_lines:
            # Check if the other municipi has a considered MM

            fita_mem_layer.selectByExpression(f'"id_linia"=\'{line_id}\'', QgsVectorLayer.SetSelection)
            for feature in fita_mem_layer.getSelectedFeatures():
                point_id_fita = coordinates_to_id_fita(feature['point_x'], feature['point_y'])
                if feature['num_termes'] == 'F2T':
                    point_id_list.append(point_id_fita)
                else:
                    pass
                    # TODO mirar en tabla linies_veines. Como hasta ahora está mal

    def remove_lines(self):
        """  """
        # TODO si se elimina, mirar si su ValidDe y su DataAlta es igual o posterior al que hay, para eliminar la línia o modificarlo
        pass

    def get_lines_to_manage(self):
        """  """
        delete_lines_list = []
        edit_lines_dict = {}
        for line_id in self.municipi_lines:
            # Check if the other municipi has a considered MM
            neighbor_ine = self.get_neighbor_ine(line_id)
            neighbor_mm = self.check_mm_exists(neighbor_ine)
            if not neighbor_mm:
                line_id_txt = line_id_2_txt(line_id)
                delete_lines_list.append(line_id_txt)
            else:
                pass
            # capa de polígonos

        return delete_lines_list, edit_lines_dict

    def get_neighbor_municipi(self, line_id):
        """  """
        line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]
        neighbor_municipi_id = ''
        if line_data['CODIMUNI1'] == self.municipi_id:
            neighbor_municipi_id = line_data['CODIMUNI2']
        elif line_data['CODIMUNI2'] == self.municipi_id:
            neighbor_municipi_id = line_data['CODIMUNI1']

        return neighbor_municipi_id

    def get_neighbor_ine(self, line_id):
        """  """
        neighbor_municipi_id = self.get_neighbor_municipi(line_id)
        neighbor_municipi_codi_ine = self.get_municipi_codi_ine(neighbor_municipi_id)

        return neighbor_municipi_codi_ine

    def get_neighbor_dates(self, neighbor_ine):
        """  """
        pass

    def remove_lines_table(self):
        """  """
        pass


def check_eliminador_input_data():
    """  """
    box = QMessageBox()
    box.setIcon(QMessageBox.Critical)
    directory_list = os.listdir(ELIMINADOR_INPUT_DIR)

    # Check that exists the input directory
    if not directory_list:
        box.setText("No hi ha cap carpeta de MMC a la carpeta d'entrades.")
        box.exec_()
        return False
    # Check that only exists one input directory
    if len(directory_list) > 1:
        box.setText("Hi ha més d'una carpeta de MMC a la carpeta d'entrades.")
        box.setText("Si us plau, esborra les que no siguin necessàries.")
        box.exec_()
        return False
    # Check that exists the input shapefiles
    directory_path = os.path.join(ELIMINADOR_INPUT_DIR, directory_list[0])
    shapefiles_list = os.listdir(directory_path)
    shapefiles_count = 0
    for shapefile in shapefiles_list:
        if ('-fita-' in shapefile or '-liniacosta-' in shapefile or '-liniacostataula-' in shapefile or '-liniaterme-' in shapefile or '-liniatermetaula-' in shapefile or '-poligon-' in shapefile or '-tallfullbt5m-' in shapefile)\
                and shapefile.endswith('.dbf'):
            shapefiles_count += 1

    if shapefiles_count == 7:
        return True
    else:
        box.setText("Falten shapefiles del MMC a la carpeta d'entrades.\nSi us plau, revisa-ho.")
        box.exec_()
        return False

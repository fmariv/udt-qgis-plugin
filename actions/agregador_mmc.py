# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the AgregadorMMC class is defined. The main function
of this class is to run the automation process that adds the newest municipal
maps to the previous layer of the Municipal Map of Catalonia.
***************************************************************************/
"""

import numpy as np
import os
import shutil
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QVariant
from qgis.core import (QgsVectorLayer,
                       QgsDataSourceUri,
                       QgsMessageLog,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransformContext,
                       QgsField,
                       QgsCoordinateTransform,
                       QgsFeature,
                       QgsGeometry,
                       QgsProject)
from qgis.core.additions.edit import edit
from PyQt5.QtWidgets import QMessageBox

from ..config import *
from ..utils import *
from .adt_postgis_connection import PgADTConnection


class AgregadorMMC(object):
    """ MMC Agregation class """

    def __init__(self):
        """  """
        # Set work layers
        points_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'fites_temp.shp'))
        lines_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'linies_temp.shp'))
        polygons_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'poligons_temp.shp'))
        coast_lines_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'linies_costa_temp.shp'))
        points_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'fitesmmc_temp.dbf'))   # TODO revisar si esta tabla debe existir
        lines_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'liniesmmc_temp.dbf'))
        coast_lines_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'linies_costammc_temp.dbf'))
        bt5_full_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'bt5m_temp.dbf'))
        # Declare input layers
        points_input_layer, lines_input_layer, polygons_input_layer, coast_lines_input_layer, coast_lines_input_table, lines_input_table, bt5_full_input_table = (None, ) * 7


    def add_municipal_map_data(self):
        """  """
        input_list_dir = os.listdir(AGREGADOR_INPUT_DIR)
        for input_dir in input_list_dir:
            self.reset_input_layers()
            input_dir_path = os.path.join(AGREGADOR_INPUT_DIR, input_dir)
            self.set_input_layers(input_dir_path)

    def reset_input_layers(self):
        """  """
        self.points_input_layer, self.lines_input_layer, self.polygons_input_layer, self.coast_lines_input_layer, self.coast_lines_input_table, self.lines_input_table, self.bt5_full_input_table = (None,) * 7

    def set_input_layers(self, directory):
        """  """
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        for file in files:
            if '-fita-' in file and file.endswith('.shp'):
                self.points_input_layer = QgsVectorLayer(os.path.join(directory, file))
            elif '-liniaterme-' in file and file.endswith('.shp'):
                self.lines_input_layer = QgsVectorLayer(os.path.join(directory, file))
            elif '-poligon-' in file and file.endswith('.shp'):
                self.polygons_input_layer = QgsVectorLayer(os.path.join(directory, file))
            elif '-liniacosta-' in file and file.endswith('.shp'):
                self.coast_lines_input_layer = QgsVectorLayer(os.path.join(directory, file))
            elif '-liniatermetaula-' in file and file.endswith('.dbf'):
                self.lines_input_table = QgsVectorLayer(os.path.join(directory, file))
            elif '-liniacostataula-' in file and file.endswith('.dbf'):
                self.coast_lines_input_table = QgsVectorLayer(os.path.join(directory, file))
            elif '-tallfullbt5m-' in file and file.endswith('.dbf'):
                self.bt5_full_input_table = QgsVectorLayer(os.path.join(directory, file))

    def add_polygons(self):
        """  """
        pass

    def add_points(self):
        """  """
        pass

    def add_lines_layer(self):
        """  """
        pass

    def add_coast_lines(self):
        """  """
        pass

    def add_lines_table(self):
        """  """
        pass

    def add_coast_lines_table(self):
        """  """
        pass

    def add_bt5_full_table(self):
        """  """
        pass


def import_agregador_data(directory_path):
    """ Import the necessary data from the input directory to the working directory """
    crs = QgsCoordinateReferenceSystem("EPSG:25831")
    input_points_layer, input_lines_layer, input_polygons_layer, input_coast_lines_layer = (None,) * 4
    input_full_bt5_table, input_point_table, input_line_table, input_coast_line_table = ('',) * 4
    # Paths
    for root, dirs, files in os.walk(directory_path):
        for file_ in files:
            if file_.endswith('_fita.shp'):
                input_points_layer = QgsVectorLayer(os.path.join(directory_path, file_))
            elif file_.endswith('_lter.shp'):
                input_lines_layer = QgsVectorLayer(os.path.join(directory_path, file_))
            elif file_.endswith('_munimmc.shp'):
                input_polygons_layer = QgsVectorLayer(os.path.join(directory_path, file_))
            elif file_.endswith('_lcos.shp'):
                input_coast_lines_layer = QgsVectorLayer(os.path.join(directory_path, file_))
            elif file_.endswith('_lcosmmc.dbf'):
                input_coast_line_table = os.path.join(directory_path, file_)
            elif file_.endswith('_fbt5m.dbf'):
                input_full_bt5_table = os.path.join(directory_path, file_)
            elif file_.endswith('_fitammc.dbf'):
                input_point_table = os.path.join(directory_path, file_)
            elif file_.endswith('ltermmc.dbf'):
                input_line_table = os.path.join(directory_path, file_)

    # Copy dbf
    shutil.copyfile(input_full_bt5_table, os.path.join(AGREGADOR_WORK_DIR, 'bt5m_temp.dbf'))
    shutil.copyfile(input_point_table, os.path.join(AGREGADOR_WORK_DIR, 'fitesmmc_temp.dbf'))
    shutil.copyfile(input_line_table, os.path.join(AGREGADOR_WORK_DIR, 'liniesmmc_temp.dbf'))
    shutil.copyfile(input_coast_line_table, os.path.join(AGREGADOR_WORK_DIR, 'linies_costammc_temp.dbf'))
    # Export layers
    QgsVectorFileWriter.writeAsVectorFormat(input_points_layer, os.path.join(AGREGADOR_WORK_DIR, 'fites_temp.shp'),
                                            'utf-8', crs, 'ESRI Shapefile')
    QgsVectorFileWriter.writeAsVectorFormat(input_lines_layer, os.path.join(AGREGADOR_WORK_DIR, 'linies_temp.shp'),
                                            'utf-8', crs, 'ESRI Shapefile')
    QgsVectorFileWriter.writeAsVectorFormat(input_polygons_layer, os.path.join(AGREGADOR_WORK_DIR, 'poligons_temp.shp'),
                                            'utf-8', crs, 'ESRI Shapefile')
    QgsVectorFileWriter.writeAsVectorFormat(input_coast_lines_layer, os.path.join(AGREGADOR_WORK_DIR, 'linies_costa_temp.shp'),
                                            'utf-8', crs, 'ESRI Shapefile')


def check_agregador_work_data():
    """ Check that exists all the necessary data in the workspace """
    file_list = os.listdir(AGREGADOR_WORK_DIR)
    if not ('bt5m_temp.dbf' in file_list and 'fites_temp.shp' in file_list and 'fitesmmc_temp.dbf' in file_list
            and 'linies_costa_temp' in file_list and 'linies_temp.shp' in file_list
            and 'liniesmmc_temp.dbf' in file_list and 'poligons_temp' in file_list):
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setText("Falten capes a la carpeta de treball.\nSi us plau, importa les dades de l'últim MMC.")
        box.exec_()

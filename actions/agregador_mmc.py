# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the AgregadorMMC class is defined. The main function
of this class is to run the automation process that adds the newest municipal
maps to the previous layer of the Municipal Map of Catalonia.
***************************************************************************/
"""

import os
import shutil
import collections

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


class AgregadorMMC():
    """ MMC Agregation class """

    def __init__(self):
        """  """
        # Set work layers
        self.points_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'fites_temp.shp'))
        self.lines_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'linies_temp.shp'))
        self.polygons_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'poligons_temp.shp'))
        self.coast_lines_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'linies_costa_temp.shp'))
        self.points_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'fitesmmc_temp.dbf'))   # TODO revisar si esta tabla debe existir
        self.lines_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'liniesmmc_temp.dbf'))
        self.coast_lines_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'linies_costammc_temp.dbf'))
        self.bt5_full_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'bt5m_temp.dbf'))
        # Declare input layers
        self.points_input_layer, self.lines_input_layer, self.polygons_input_layer, self.coast_lines_input_layer, self.coast_lines_input_table, self.lines_input_table, self.bt5_full_input_table = (None, ) * 7

    # #######################
    # Add data
    def add_municipal_map_data(self):
        """  """
        input_list_dir = os.listdir(AGREGADOR_INPUT_DIR)
        for input_dir in input_list_dir:
            self.reset_input_layers()
            input_dir_path = os.path.join(AGREGADOR_INPUT_DIR, input_dir)
            self.set_input_layers(input_dir_path)
            # Add geometries
            self.add_polygons()
            self.add_points()
            self.add_lines_layer()
            self.add_coast_lines_layer()
            # Add tables
            self.add_lines_table()
            self.add_coast_lines_table()
            self.add_bt5_full_table()

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
        polygons_features = self.polygons_input_layer.getFeatures()
        with edit(self.polygons_work_layer):
            for polygon in polygons_features:
                self.polygons_work_layer.addFeature(polygon)

    def add_points(self):
        """  """
        # Get a list with all the points ID
        fita_id_list = self.get_points_id_list()

        points_features = self.points_input_layer.getFeatures()
        with edit(self.points_work_layer):
            for point in points_features:
                # This is done in order to avoid adding duplicated features
                # TODO test
                if not point['IdFita'] in fita_id_list:
                    geom = point.geometry()
                    fet = QgsFeature()
                    fet.setGeometry(geom)
                    fet.setAttributes([point['IdFita']])
                    self.points_work_layer.addFeature(fet)

    def add_lines_layer(self):
        """  """
        line_id_list = self.get_lines_id_list('layer')

        lines_features = self.lines_input_layer.getFeatures()
        with edit(self.lines_work_layer):
            for line in lines_features:
                if not line['IdLinia'] in line_id_list:   # TODO test
                    self.lines_work_layer.addFeature(line)

    def add_coast_lines_layer(self):
        """  """
        coast_lines_features = self.coast_lines_input_layer.getFeatures()
        with edit(self.coast_lines_work_layer):
            for coast_line in coast_lines_features:
                self.coast_lines_work_layer.addFeature(coast_line)

    def add_lines_table(self):
        """  """
        line_id_list = self.get_lines_id_list('table')

        lines_features = self.lines_input_table.getFeatures()
        with edit(self.lines_work_table):
            for line in lines_features:
                if not line['IdLinia'] in line_id_list:   # TODO test
                    self.lines_work_table.addFeature(line)

    def add_coast_lines_table(self):
        """  """
        coast_lines_features = self.coast_lines_input_table.getFeatures()
        with edit(self.coast_lines_work_table):
            for coast_line in coast_lines_features:
                self.coast_lines_work_table.addFeature(coast_line)

    def add_bt5_full_table(self):
        """  """
        fulls_features = self.bt5_full_input_table.getFeatures()
        with edit(self.bt5_full_work_table):
            for full in fulls_features:
                self.bt5_full_work_table.addFeature(full)

    def get_points_id_list(self):
        """  """
        fita_id_list = []
        for feat in self.points_work_layer.getFeatures():
            fita_id_list.append(feat['IdFita'])

        return fita_id_list

    def get_lines_id_list(self, entity):
        """  """
        line_id_list = []
        layer = None

        if entity == 'layer':
            layer = self.lines_work_layer
        elif entity == 'table':
            layer = self.lines_work_table

        for feat in layer.getFeatures():
            line_id_list.append(feat['IdLinia'])

        return line_id_list


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


def check_agregador_input_data():
    """ Check that exists all the necessary data in the workspace """
    file_list = os.listdir(AGREGADOR_WORK_DIR)
    if not ('bt5m_temp.dbf' in file_list and 'fites_temp.shp' in file_list and 'fitesmmc_temp.dbf' in file_list \
            and 'linies_costa_temp.shp' in file_list and 'linies_temp.shp' in file_list \
            and 'liniesmmc_temp.dbf' in file_list and 'poligons_temp.shp' in file_list):
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setText("Falten capes a la carpeta de treball.\nSi us plau, importa les dades de l'últim MMC.")
        box.exec_()
        return False

    return True
# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the AgregadorMMC class is defined. The main function
of this class is to run the automation process that adds the newest municipal
maps to the previous layer of the Municipal Map of Catalonia.
***************************************************************************/
"""

from datetime import datetime
import os
import shutil

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


class AgregadorMMC:
    """ MMC Agregation class """

    def __init__(self):
        # Initialize instance attributes
        # Common
        self.current_date = datetime.now().strftime("%Y%m%d")
        self.crs = QgsCoordinateReferenceSystem("EPSG:25831")
        # Set work layers
        self.points_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'fites_temp.shp'), 'Fites')
        self.lines_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'linies_temp.shp'), 'Linies de terme')
        self.polygons_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'poligons_temp.shp'), 'Poligons')
        self.coast_lines_work_layer = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'linies_costa_temp.shp'), 'Linies de costa')
        self.points_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'fitesmmc_temp.dbf'), 'Fites - taula')   # TODO revisar si esta tabla debe existir
        self.lines_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'liniesmmc_temp.dbf'), 'Linies de terme - taula')
        self.coast_lines_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'linies_costammc_temp.dbf'), 'Linies de costa - taula')
        self.bt5_full_work_table = QgsVectorLayer(os.path.join(AGREGADOR_WORK_DIR, 'bt5m_temp.dbf'), 'Fulls BT5M')
        self.layers = (self.points_work_table, self.lines_work_table, self.coast_lines_work_table, self.bt5_full_work_table,
                       self.lines_work_layer, self.polygons_work_layer, self.coast_lines_work_layer, self.points_work_layer)
        # Declare input layers
        self.points_input_layer, self.lines_input_layer, self.polygons_input_layer, self.coast_lines_input_layer, self.coast_lines_input_table, self.lines_input_table, self.bt5_full_input_table = (None, ) * 7
        # Output directory
        self.output_directory = None

    # #######################
    # Add data
    def add_municipal_map_data(self):
        """
        Add the input municipal maps features to the last Municipal Map of Catalonia. Features include:
            - Points
            - Lines
            - Polygons
            - Coast lines
            - Lines - table
            - Coast lines - table
            - BT5M
        """
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
        """ Reset the input QgsVectorLayers to None to avoid over writing """
        self.points_input_layer, self.lines_input_layer, self.polygons_input_layer, self.coast_lines_input_layer, self.coast_lines_input_table, self.lines_input_table, self.bt5_full_input_table = (None,) * 7

    def set_input_layers(self, directory):
        """ Set the input QgsVectorLayers that are going to be added to the working layers """
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
        """ Add the input polygons to the Municipal Map of Catalonia """
        polygons_features = self.polygons_input_layer.getFeatures()
        with edit(self.polygons_work_layer):
            for polygon in polygons_features:
                self.polygons_work_layer.addFeature(polygon)

    def add_points(self):
        """ Add the input points to the Municipal Map of Catalonia """
        points_features = self.points_input_layer.getFeatures()
        with edit(self.points_work_layer):
            for point in points_features:
                # Get a list with all the points ID
                fita_id_list = self.get_points_id_list()
                # This is done in order to avoid adding duplicated features
                if not point['IdFita'] in fita_id_list:
                    geom = point.geometry()
                    fet = QgsFeature()
                    fet.setGeometry(geom)
                    fet.setAttributes([point['IdFita']])
                    self.points_work_layer.addFeature(fet)

    def add_lines_layer(self):
        """ Add the input lines to the Municipal Map of Catalonia """
        line_id_list = self.get_lines_id_list('layer')

        lines_features = self.lines_input_layer.getFeatures()
        with edit(self.lines_work_layer):
            for line in lines_features:
                if not line['IdLinia'] in line_id_list:
                    self.lines_work_layer.addFeature(line)

    def add_coast_lines_layer(self):
        """ Add the input coast lines to the Municipal Map of Catalonia """
        coast_lines_features = self.coast_lines_input_layer.getFeatures()
        with edit(self.coast_lines_work_layer):
            for coast_line in coast_lines_features:
                self.coast_lines_work_layer.addFeature(coast_line)

    def add_lines_table(self):
        """ Add the input lines to the table of the Municipal Map of Catalonia """
        line_id_list = self.get_lines_id_list('table')

        lines_features = self.lines_input_table.getFeatures()
        with edit(self.lines_work_table):
            for line in lines_features:
                if not line['IdLinia'] in line_id_list:
                    self.lines_work_table.addFeature(line)

    def add_coast_lines_table(self):
        """ Add the input coast lines to the table of the Municipal Map of Catalonia """
        coast_lines_features = self.coast_lines_input_table.getFeatures()
        with edit(self.coast_lines_work_table):
            for coast_line in coast_lines_features:
                self.coast_lines_work_table.addFeature(coast_line)

    def add_bt5_full_table(self):
        """ Add the input BT5M table of the Municipal Map of Catalonia """
        fulls_features = self.bt5_full_input_table.getFeatures()
        with edit(self.bt5_full_work_table):
            for full in fulls_features:
                self.bt5_full_work_table.addFeature(full)

    def get_points_id_list(self):
        """ Get a list with all the points ID of the point working laye """
        fita_id_list = []
        for feat in self.points_work_layer.getFeatures():
            fita_id_list.append(feat['IdFita'])

        return fita_id_list

    def get_lines_id_list(self, entity):
        """ Get a list with all the lines ID of the line working layer """
        line_id_list = []
        layer = None

        if entity == 'layer':
            layer = self.lines_work_layer
        elif entity == 'table':
            layer = self.lines_work_table

        for feat in layer.getFeatures():
            line_id_list.append(feat['IdLinia'])

        return line_id_list

    # #######################
    # Export data
    def export_municipal_map_data(self):
        """ Export the new Municipal Map of Catalonia to the output directory """
        self.create_output_directory()
        # Set output layer or table names
        output_points_layer = f'mapa-municipal-catalunya-fita-{self.current_date}.shp'
        output_lines_layer = f'mapa-municipal-catalunya-liniaterme-{self.current_date}.shp'
        output_polygon_layer = f'mapa-municipal-catalunya-poligon-{self.current_date}.shp'
        output_lines_table = f'mapa-municipal-catalunya-liniatermetaula-{self.current_date}.shp'
        output_coast_line_layer = f'mapa-municipal-catalunya-liniacosta-{self.current_date}.shp'
        output_coast_line_table = f'mapa-municipal-catalunya-liniacostataula-{self.current_date}.shp'
        output_coast_line_full = f'mapa-municipal-catalunya-tallfullbt5m-{self.current_date}.shp'
        # Export the data
        QgsVectorFileWriter.writeAsVectorFormat(self.points_work_layer,
                                                os.path.join(self.output_directory, output_points_layer),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.lines_work_layer,
                                                os.path.join(self.output_directory, output_lines_layer),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.polygons_work_layer,
                                                os.path.join(self.output_directory, output_polygon_layer),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.lines_work_table,
                                                os.path.join(self.output_directory, output_lines_table),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.coast_lines_work_layer,
                                                os.path.join(self.output_directory, output_coast_line_layer),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.coast_lines_work_table,
                                                os.path.join(self.output_directory, output_coast_line_table),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.bt5_full_work_table,
                                                os.path.join(self.output_directory, output_coast_line_full),
                                                'utf-8', self.crs, 'ESRI Shapefile')

    def create_output_directory(self):
        """ Create the output directory of the new Municipal Map of Catalonia """
        directory_name = f'mapa-municipal-catalunya-{self.current_date}'
        directory_path = os.path.join(AGREGADOR_OUTPUT_DIR, directory_name)
        if os.path.exists(directory_path):
            shutil.rmtree(directory_path)
        os.mkdir(directory_path)

        self.output_directory = directory_path

    def add_layers_canvas(self):
        """ Add the working layers to the QGIS canvas """
        registry = QgsProject.instance()
        for layer in self.layers:
            layer_exists = len(QgsProject.instance().mapLayersByName(layer.name())) != 0
            if layer_exists:
                registry.removeAllMapLayers()
            registry.addMapLayer(layer)

    @staticmethod
    def remove_layers_canvas():
        """ Remove the working layers from the QGIS canvas """
        registry = QgsProject.instance()
        registry.removeAllMapLayers()


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


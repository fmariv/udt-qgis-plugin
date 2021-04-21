# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the GeneradorMMC class is defined. The main function
of this class is to run the automation process that exports the geometries
and generates the metadata of a municipal map.
***************************************************************************/
"""
import numpy as np
import os

from qgis.core import QgsVectorLayer, QgsDataSourceUri, QgsMessageLog, QgsVectorFileWriter, QgsCoordinateReferenceSystem, \
    QgsCoordinateTransformContext
from PyQt5.QtWidgets import QMessageBox

from ..config import *
from .adt_postgis_connection import PgADTConnection

# Masquefa ID = 494


class GeneradorMMC(object):

    def __init__(self, municipi_id, data_alta):
        # Initialize instance attributes
        # Common
        self.arr_name_municipis = np.genfromtxt(DIC_NOM_MUNICIPIS, dtype=None, encoding=None, delimiter=',', names=True)
        self.crs = QgsCoordinateReferenceSystem("EPSG:25831")
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        # Municipi dependant
        self.municipi_id = int(municipi_id)
        self.data_alta = data_alta
        self.municipi_normalized_name = self.get_municipi_normalized_name()
        self.municipi_input_dir = os.path.join(GENERADOR_INPUT_DIR, self.municipi_normalized_name)
        self.shapefiles_input_dir = os.path.join(self.municipi_input_dir, SHAPEFILES_PATH)

    def get_municipi_normalized_name(self):
        """ Get the municipi's normalized name, without accent marks or special characters """
        muni_data = self.arr_name_municipis[np.where(self.arr_name_municipis['id_area'] == self.municipi_id)]
        muni_norm_name = muni_data['nom_muni_norm'][0]

        return muni_norm_name

    def start_process(self):
        """ Main entry point """
        # Control that the input dir and all the input data exist
        inputs_valid = self.validate_inputs()
        if not inputs_valid:
            return
        # Copy data to work directory
        self.copy_data_to_work()
        # Set the layers paths if exist
        work_point_layer, work_line_layer, polygon_line_layer = self.set_layers_paths()
        # ########################
        # Start generating process
        # Fites
        generador_mmc_fites = GeneradorMMCFites(self.municipi_id, self.data_alta, work_point_layer)
        generador_mmc_fites.generate_fites_layer()

    def validate_inputs(self):
        """ Validate that all the inputs exists and are correct """
        municipi_input_dir_exists = self.check_municipi_input_dir()
        if not municipi_input_dir_exists:
            return False
        municipi_input_data_ok = self.check_municipi_input_data()
        if not municipi_input_data_ok:
            return False

        return True

    def check_municipi_input_dir(self):
        """ Check that exists the municipi's folder into the inputs directory """
        if not os.path.exists(self.municipi_input_dir):
            e_box = QMessageBox()
            e_box.setIcon(QMessageBox.Warning)
            e_box.setText(f"No existeix la carpeta del municipi al directori d'entrades. El nom que ha de tenir "
                          f"es '{self.municipi_normalized_name}'.")
            e_box.exec_()
            return False
        else:
            return True

    def check_municipi_input_data(self):
        """ Check that exists the Shapefiles' folder and all the shapefiles needed """
        if not os.path.exists(self.shapefiles_input_dir):
            e_box = QMessageBox()
            e_box.setIcon(QMessageBox.Warning)
            e_box.setText("No existeix la carpeta de Shapefiles a la carpeta del municipi")
            e_box.exec_()
            return False

        shapefiles_list = os.listdir(self.shapefiles_input_dir)
        for layer in ('MM_Fites.shp', 'MM_Linies.shp', 'MM_Poligons.shp'):
            if layer not in shapefiles_list:
                e_box = QMessageBox()
                e_box.setIcon(QMessageBox.Warning)
                e_box.setText(f"No existeix la capa {layer} a la carpeta de Shapefiles del municipi")
                e_box.exec_()
                return False
                # TODO solo devuelve si falta una capa. Que abra diferentes ventanas si falta 1 o + de 1

        return True

    def copy_data_to_work(self):
        """ Import input data to the work directory """
        # Set paths
        input_points_layer = QgsVectorLayer(os.path.join(self.shapefiles_input_dir, 'MM_Fites.shp'))
        input_lines_layer = QgsVectorLayer(os.path.join(self.shapefiles_input_dir, 'MM_Linies.shp'))
        input_polygon_layer = QgsVectorLayer(os.path.join(self.shapefiles_input_dir, 'MM_Poligons.shp'))
        # Export
        # TODO make as loop for
        QgsVectorFileWriter.writeAsVectorFormat(input_points_layer, os.path.join(GENERADOR_WORK_DIR, 'MM_Fites.shp'),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(input_lines_layer, os.path.join(GENERADOR_WORK_DIR, 'MM_Linies.shp'),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(input_polygon_layer, os.path.join(GENERADOR_WORK_DIR, 'MM_Poligons.shp'),
                                                'utf-8', self.crs, 'ESRI Shapefile')

    @staticmethod
    def set_layers_paths():
        """ Set the paths to the layers and directories to be managed """
        points_layer = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_Fites.shp'))
        lines_layer = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_Linies.shp'))
        polygon_layer = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_Poligons.shp'))

        return points_layer, lines_layer, polygon_layer


class GeneradorMMCFites(GeneradorMMC):

    def __init__(self, municipi_id, data_alta, fites_layer):
        GeneradorMMC.__init__(self, municipi_id, data_alta)
        self.points_layer = fites_layer

    def generate_fites_layer(self):
        """ Main entry point """


# VALIDATORS
def validate_municipi_id(municipi_id):
    """ Check and validate the Municipi ID input for the Generador MMC class """
    # Validate Municipi ID
    if not municipi_id:
        e_box = QMessageBox()
        e_box.setIcon(QMessageBox.Critical)
        e_box.setText("No s'ha indicat cap ID de municipi")
        e_box.exec_()
        return False

    return True


def validate_data_alta(new_data_alta):
    """ Check and validate the Data alta input for the Generador MMC class """
    # Validate the input date format is correct
    if len(new_data_alta) != 8:
        e_box = QMessageBox()
        e_box.setIcon(QMessageBox.Critical)
        e_box.setText("La Data Alta no és correcte")
        e_box.exec_()
        return False

    return True

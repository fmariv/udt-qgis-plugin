# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the GeneradorMMC class is defined. The main function
of this class is to run the automation process that exports the geometries
and generates the metadata of a municipal map.
***************************************************************************/
"""

import datetime
import numpy as np
import os

from PyQt5.QtCore import QVariant
from qgis.core import QgsVectorLayer, QgsDataSourceUri, QgsMessageLog, QgsVectorFileWriter, QgsCoordinateReferenceSystem, \
    QgsCoordinateTransformContext, QgsField
from PyQt5.QtWidgets import QMessageBox

from ..config import *
from .adt_postgis_connection import PgADTConnection

# Masquefa ID = 494
# 081192


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
        self.municipi_name = self.get_municipi_name()
        self.municipi_normalized_name = self.get_municipi_normalized_name()
        self.municipi_codi_ine = self.get_municipi_codi_ine()
        self.municipi_valid_de = self.get_municipi_valid_de()
        self.municipi_input_dir = os.path.join(GENERADOR_INPUT_DIR, self.municipi_normalized_name)
        self.shapefiles_input_dir = os.path.join(self.municipi_input_dir, SHAPEFILES_PATH)

    def get_municipi_name(self):
        """  """
        muni_data = self.arr_name_municipis[np.where(self.arr_name_municipis['id_area'] == self.municipi_id)]
        muni_name = muni_data['nom_muni'][0]

        return muni_name

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
        work_point_layer, work_line_layer, work_polygon_layer = self.set_layers_paths()
        # Get a dictionary with all the ValidDe dates per line
        dict_valid_de = self.get_lines_valid_de(work_line_layer)
        # ########################
        # Start generating process
        # Fites
        generador_mmc_fites = GeneradorMMCFites(self.municipi_id, self.data_alta, work_point_layer, dict_valid_de)
        generador_mmc_fites.generate_fites_layer()
        # Poligon
        generador_mmc_polygon = GeneradorMMCPolygon(self.municipi_id, self.data_alta, work_polygon_layer)
        generador_mmc_polygon.generate_polygon_layer()

        # DEBUG
        e_box = QMessageBox()
        e_box.setIcon(QMessageBox.Information)
        e_box.setText("Capes generades")
        e_box.exec_()

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

    # TODO conseguir ValidDe (data cdt) de cada linia
    def get_lines_valid_de(self, lines_layer):
        """
        Get the ValidDe date from every line that conform the municipi's boundary. Each date is equal to the
        CDT date from the memories_treb_top table
        """
        self.pg_adt.connect()
        dict_valid_de = {}
        mtt_table = self.pg_adt.get_table('memoria_treb_top')
        for line in lines_layer.getFeatures():
            line_id = line['id_linia']
            mtt_table.selectByExpression(f'"id_linia"=\'{line_id}\' and "vig_mtt" is True', QgsVectorLayer.SetSelection)
            for feature in mtt_table.getSelectedFeatures():
                line_cdt = feature['data_cdt']
                line_cdt_str = line_cdt.toString('yyyyMMdd')
                dict_valid_de[line_id] = line_cdt_str

        return dict_valid_de

    def get_municipi_valid_de(self):
        """  """
        self.pg_adt.connect()
        mapa_muni_table = self.pg_adt.get_table('mapa_muni_icc')
        municipi_codi_ine = self.municipi_codi_ine.replace("\"", "'")
        mapa_muni_table.selectByExpression(f'"codi_muni"={municipi_codi_ine} and "vig_mm" is True',
                                           QgsVectorLayer.SetSelection)
        for feature in mapa_muni_table.getSelectedFeatures():
            municipi_cdt = feature['data_con_cdt']
            municipi_cdt_str = municipi_cdt.toString('yyyyMMdd')

        return municipi_cdt_str

    def get_municipi_codi_ine(self):
        """  """
        muni_data = self.arr_name_municipis[np.where(self.arr_name_municipis['id_area'] == self.municipi_id)]
        codi_ine = muni_data['codi_ine_muni'][0]

        return codi_ine


class GeneradorMMCFites(GeneradorMMC):

    def __init__(self, municipi_id, data_alta, fites_layer, dict_valid_de):
        GeneradorMMC.__init__(self, municipi_id, data_alta)
        self.points_layer = fites_layer
        self.dict_valid_de = dict_valid_de

    def generate_fites_layer(self):
        """ Main entry point """
        # TODO por fita, query y poner resultados. Es poco eficiente pero es lo unico que se me ocurre...
        self.delete_fields()
        self.add_fields()
        self.fill_fields()
        self.delete_fields(True)

    def delete_fields(self, remainder_fields=False):
        """ Delete non necessary fields """
        # List of indices of the fields to be deleted. The deleteAttributes method doesn't catch fields by name but
        # by index instead
        if remainder_fields:
            delete_fields_list = list((0, 1))
        else:
            delete_fields_list = list((2, 3, 4, 5, 6, 7))
        self.points_layer.dataProvider().deleteAttributes(delete_fields_list)
        self.points_layer.updateFields()

    def add_fields(self):
        """ Add necessary fields """
        # Set new fields
        id_u_fita_field = QgsField(name='IdUfita', type=QVariant.String, typeName='text', len=10)
        id_fita_field = QgsField(name='IdFita', type=QVariant.String, typeName='text', len=18)
        id_sector_field = QgsField(name='IdSector', type=QVariant.String, typeName='text', len=1)
        id_fita_r_field = QgsField(name='IdFitaR', type=QVariant.String, typeName='text', len=3)
        num_termes_field = QgsField(name='NumTermes', type=QVariant.String, typeName='text', len=3)
        monument_field = QgsField(name='Monument', type=QVariant.String, typeName='text', len=1)
        valid_de_field = QgsField(name='ValidDe', type=QVariant.String, typeName='text', len=8)
        valid_a_field = QgsField(name='ValidA', type=QVariant.String, typeName='text', len=8)
        data_alta_field = QgsField(name='DataAlta', type=QVariant.String, typeName='text', len=12)
        data_baixa_field = QgsField(name='DataBaixa', type=QVariant.String, typeName='text', len=12)
        id_linia_field = QgsField(name='IdLinia', type=QVariant.String, typeName='text', len=4)
        new_fields_list = [id_u_fita_field, id_fita_field, id_sector_field, id_fita_r_field, num_termes_field,
                           monument_field, valid_de_field, valid_a_field, data_alta_field, data_baixa_field,
                           id_linia_field]
        self.points_layer.dataProvider().addAttributes(new_fields_list)
        self.points_layer.updateFields()

    def fill_fields(self):
        """ Fill the layer's fields """
        self.pg_adt.connect()
        fita_mem_layer = self.pg_adt.get_layer('v_fita_mem', 'id_fita')

        self.points_layer.startEditing()
        for point in self.points_layer.getFeatures():
            point_id = point['id_punt']
            fita_mem_layer.selectByExpression(f'"id_punt"=\'{point_id}\'', QgsVectorLayer.SetSelection)
            for feature in fita_mem_layer.getSelectedFeatures():
                point_id_u_fita = feature['id_u_fita']
                point_id_fita = self.coordinates_to_id_fita(feature['point_x'], feature['point_y'])
                point_r_fita = self.point_num_to_text(feature['num_fita'])
                point_sector = feature['num_sector']
                point_num_termes = feature['num_termes']
                point_monumentat = feature['trobada']

            point['IdUFita'] = point_id_u_fita[:-2]
            point['IdFita'] = point_id_fita
            point['IdFitaR'] = point_r_fita
            point['IdSector'] = point_sector
            point['NumTermes'] = point_num_termes
            point['IdLinia'] = point['id_linia']
            point['DataAlta'] = self.data_alta
            point['ValidDe'] = self.dict_valid_de[point['id_linia']]
            if point_monumentat is True:
                point['Monument'] = 'S'
            else:
                point['Monument'] = 'N'

            self.points_layer.updateFeature(point)

        self.points_layer.commitChanges()

    @staticmethod
    def point_num_to_text(num_fita):
        """ Transform point's order number into text """
        num_fita = int(num_fita)
        num_fita_str = str(num_fita)
        if len(num_fita_str) == 1:
            num_fita_txt = "00" + num_fita_str
        elif len(num_fita_str) == 2:
            num_fita_txt = "0" + num_fita_str
        else:
            num_fita_txt = num_fita_str

        return num_fita_txt

    @staticmethod
    def coordinates_to_id_fita(coord_x, coord_y):
        """  """
        x = str(round(coord_x, 1))
        y = str(round(coord_y, 1))
        x = x.replace(',', '.')
        y = y.replace(',', '.')
        id_fita = f'{x}_{y}'

        return id_fita


class GeneradorMMCPolygon(GeneradorMMC):

    def __init__(self, municipi_id, data_alta, polygon_layer):
        GeneradorMMC.__init__(self, municipi_id, data_alta)
        self.polygon_layer = polygon_layer

    def generate_polygon_layer(self):
        """ Main entry point """
        self.add_fields()
        self.fill_fields()
        self.delete_fields()

    def delete_fields(self):
        """  """
        self.polygon_layer.dataProvider().deleteAttributes([0])
        self.polygon_layer.updateFields()

    def add_fields(self):
        """ Add necessary fields """
        # Set new fields
        codi_muni_field = QgsField(name='CodiMuni', type=QVariant.String, typeName='text', len=6)
        area_muni_field = QgsField(name='AreaMunMMC', type=QVariant.String, typeName='text', len=8)
        name_muni_field = QgsField(name='NomMuni', type=QVariant.String, typeName='text', len=100)
        valid_de_field = QgsField(name='ValidDe', type=QVariant.String, typeName='text', len=8)
        valid_a_field = QgsField(name='ValidA', type=QVariant.String, typeName='text', len=8)
        data_alta_field = QgsField(name='DataAlta', type=QVariant.String, typeName='text', len=12)
        data_baixa_field = QgsField(name='DataBaixa', type=QVariant.String, typeName='text', len=12)
        new_fields_list = [codi_muni_field, area_muni_field, name_muni_field, valid_de_field, valid_a_field,
                           data_alta_field, data_baixa_field]
        self.polygon_layer.dataProvider().addAttributes(new_fields_list)
        self.polygon_layer.updateFields()

    def fill_fields(self):
        """  """
        self.polygon_layer.startEditing()
        for polygon in self.polygon_layer.getFeatures():
            codi_ine = self.municipi_codi_ine.replace('"', '')
            polygon['CodiMuni'] = codi_ine
            polygon['AreaMunMMC'] = polygon['Sup_CDT']
            polygon['NomMuni'] = str(self.municipi_name)
            polygon['ValidDe'] = self.municipi_valid_de
            polygon['DataAlta'] = self.data_alta
            self.polygon_layer.updateFeature(polygon)

        self.polygon_layer.commitChanges()


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

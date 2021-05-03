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
import shutil

from PyQt5.QtCore import QVariant
from qgis.core import QgsVectorLayer, QgsDataSourceUri, QgsMessageLog, QgsVectorFileWriter, QgsCoordinateReferenceSystem, \
    QgsCoordinateTransformContext, QgsField, QgsCoordinateTransform, QgsFeature, QgsGeometry, QgsProject
from PyQt5.QtWidgets import QMessageBox

from ..config import *
from .adt_postgis_connection import PgADTConnection

# Masquefa ID = 494
# 081192


class GeneradorMMC(object):

    def __init__(self, municipi_id, data_alta=None, coast=False):
        # Initialize instance attributes
        # Common
        self.arr_name_municipis = np.genfromtxt(DIC_NOM_MUNICIPIS, dtype=None, encoding=None, delimiter=',', names=True)
        self.arr_lines_data = np.genfromtxt(DIC_LINES, dtype=None, encoding=None, delimiter=';', names=True)
        self.crs = QgsCoordinateReferenceSystem("EPSG:25831")
        self.crs_geo = QgsCoordinateReferenceSystem("EPSG:4258")
        self.entities_list = ('fita', 'liniacosta', 'liniacostaula', 'liniaterme', 'liniatermetaula', 'poligon',
                              'tallfullbt5m')
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        # ###
        # Input dependant that don't need data from the layers
        self.municipi_id = int(municipi_id)
        self.data_alta = data_alta
        self.coast = coast
        self.municipi_name = self.get_municipi_name()
        self.municipi_normalized_name = self.get_municipi_normalized_name()
        self.municipi_codi_ine = self.get_municipi_codi_ine()
        self.municipi_valid_de = self.get_municipi_valid_de()
        self.municipi_metadata_table = self.get_municipi_metadata_table()   # Can be None
        # ###
        # Input dependant that need data from the line layer
        # Paths
        self.municipi_input_dir = os.path.join(GENERADOR_INPUT_DIR, self.municipi_normalized_name)
        self.shapefiles_input_dir = os.path.join(self.municipi_input_dir, SHAPEFILES_PATH)
        self.output_directory_name = f'mapa-municipal-{self.municipi_normalized_name}-{self.municipi_valid_de}'
        self.output_directory_path = os.path.join(GENERADOR_OUTPUT_DIR, self.output_directory_name)
        self.output_subdirectory_path = os.path.join(self.output_directory_path, self.output_directory_name)
        self.report_path = os.path.join(self.output_directory_path, f'{str(municipi_id)}_Report.txt')
        # Input line layer as Vector Layer for getting some data related to the lines ID
        self.input_line_layer = QgsVectorLayer(os.path.join(self.shapefiles_input_dir, 'MM_Linies.shp'))
        # Get a list with all the lines ID
        self.municipi_lines = self.get_municipi_lines(self.input_line_layer)
        if not self.coast:
            self.municipi_coast_line = 'Aquest MM no te linia de costa.'
        else:
            self.municipi_coast_line = self.get_municipi_coast_line(self.input_line_layer)
        # Get a dictionary with all the ValidDe dates per line
        self.dict_valid_de = self.get_lines_valid_de(self.input_line_layer)
        # Get a dictionary with the municipis' names per line
        self.municipis_names_lines = self.get_municipis_names_line()

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

    def get_municipi_lines(self, lines_layer):
        """ """
        line_list = []
        for line in lines_layer.getFeatures():
            line_id = line['id_linia']
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]
            if line_data['LIMCOSTA'] == 'N':
                line_list.append(line_id)

        return line_list

    def get_municipi_coast_line(self, lines_layer):
        coast_line_id = ''
        for line in lines_layer.getFeatures():
            line_id = line['id_linia']
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]
            if line_data['LIMCOSTA'] == 'S':
                coast_line_id = line_id

        return coast_line_id

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
        mapa_muni_table.selectByExpression(f'"codi_muni"=\'{self.municipi_codi_ine}\' and "vig_mm" is True',
                                           QgsVectorLayer.SetSelection)
        municipi_cdt_str = ''
        for feature in mapa_muni_table.getSelectedFeatures():
            municipi_cdt = feature['data_con_cdt']
            municipi_cdt_str = municipi_cdt.toString('yyyyMMdd')

        return municipi_cdt_str

    def get_municipi_codi_ine(self):
        """  """
        muni_data = self.arr_name_municipis[np.where(self.arr_name_municipis['id_area'] == self.municipi_id)]
        codi_ine = muni_data['codi_ine_muni'][0].strip('"\'')

        return codi_ine

    def get_municipi_metadata_table(self):
        """  """
        metadata_table_name = f'{self.municipi_id}_Taula_espect_C4.dbf'
        metadata_table_path = os.path.join(GENERADOR_TAULES_ESPEC, metadata_table_name)

        if os.path.exists(metadata_table_path):
            return QgsVectorLayer(metadata_table_path)
        else:
            return ''

    def get_municipis_names_line(self):
        """  """
        municipis_names_line = {}
        for line_id in self.municipi_lines:
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == int(line_id))]
            name_muni_1 = line_data['NOMMUNI1'][0]
            name_muni_2 = line_data['NOMMUNI2'][0]
            municipis_names_line[line_id] = (name_muni_1, name_muni_2)

        return municipis_names_line

    def open_report(self):
        """  """
        if os.path.exists(self.report_path):
            os.startfile(self.report_path, 'open')
        else:
            e_box = QMessageBox()
            e_box.setIcon(QMessageBox.Critical)
            e_box.setText("No existeix cap arxiu de report")
            e_box.exec_()
            return

    def call_generate_mmc_layers(self):
        """  """
        generador_mmc_layers = GeneradorMMCLayers(self.municipi_id, self.data_alta)
        generador_mmc_layers.generate_mmc_layers()

    def call_generate_metadata_table(self):
        """  """
        generador_mmc_metadata_table = GeneradorMMCMetadataTable(self.municipi_id, self.data_alta)
        generador_mmc_metadata_table.generate_metadata_table()


class GeneradorMMCLayers(GeneradorMMC):

    def __init__(self, municipi_id, data_alta, coast=False):
        GeneradorMMC.__init__(self, municipi_id, data_alta, coast)
        # Work layers paths
        self.work_point_layer = None
        self.work_line_layer = None
        self.work_polygon_layer = None
        self.work_lines_table = None
        self.work_coast_line_layer = None
        self.work_coast_line_table = None
        self.work_coast_line_full = None
        self.municipi_superficie_cdt = None
        # Bounding box coordinates
        self.y_min = None
        self.y_max = None
        self.x_min = None
        self.x_max = None
        # Instances
        self.generador_mmc_polygon = None

    def generate_mmc_layers(self):
        """ Main entry point """
        # ########################
        # SET DATA
        # Copy data to work directory
        self.copy_data_to_work()
        # Set the layers paths
        self.work_point_layer, self.work_line_layer, self.work_polygon_layer = self.set_layers_paths()

        # ########################
        # LAYERS GENERATION PROCESS
        # Lines
        generador_mmc_lines = GeneradorMMCLines(self.municipi_id, self.data_alta, self.work_line_layer,
                                                self.dict_valid_de, self.coast)
        generador_mmc_lines.generate_lines_layer()   # Layer
        self.work_lines_table = generador_mmc_lines.generate_lines_table()   # Table
        # Fites
        generador_mmc_fites = GeneradorMMCFites(self.municipi_id, self.data_alta, self.work_point_layer,
                                                self.dict_valid_de)
        generador_mmc_fites.generate_fites_layer()
        # Polygon
        self.generador_mmc_polygon = GeneradorMMCPolygon(self.municipi_id, self.data_alta, self.work_polygon_layer)
        self.generador_mmc_polygon.generate_polygon_layer()
        # Costa
        generador_mmc_costa = GeneradorMMCCosta(self.municipi_id, self.data_alta, self.work_line_layer,
                                                self.dict_valid_de, self.coast)
        self.work_coast_line_layer = generador_mmc_costa.generate_coast_line_layer()
        self.work_coast_line_table = generador_mmc_costa.generate_coast_line_table()
        self.work_coast_line_full = generador_mmc_costa.generate_coast_full_bt5m_table()

        ##########################
        # DATA EXPORTING
        # Make the output directories if they don't exist
        self.make_output_directories()
        # Write the output report
        self.write_report()
        # Export the data to the output directory
        self.export_data()
        # Remove the temp files
        remove_generador_temp_files()

    def copy_data_to_work(self):
        """ Import input data to the work directory """
        # Set paths
        input_points_layer = QgsVectorLayer(os.path.join(self.shapefiles_input_dir, 'MM_Fites.shp'))
        input_lines_layer = QgsVectorLayer(os.path.join(self.shapefiles_input_dir, 'MM_Linies.shp'))
        input_polygon_layer = QgsVectorLayer(os.path.join(self.shapefiles_input_dir, 'MM_Poligons.shp'))
        # Export
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

    def make_output_directories(self):
        """ """
        # Create directories #######
        # Create output directory
        if os.path.exists(self.output_directory_path):
            shutil.rmtree(self.output_directory_path)
        os.mkdir(self.output_directory_path)
        # Create output subdirectory with the same name
        if os.path.exists(self.output_subdirectory_path):
            shutil.rmtree(self.output_subdirectory_path)
        os.mkdir(self.output_subdirectory_path)

    def write_report(self):
        """  """
        # Remove the report if it already exists
        if os.path.exists(self.report_path):
            os.remove(self.report_path)
        # Set the report info
        self.set_polygon_info()
        # Write the report
        with open(self.report_path, 'a+') as f:
            f.write("--------------------------------------------------------------------\n")
            f.write(f"REPORT DEL MM: {self.municipi_name} (considerat: {self.municipi_valid_de})\n")
            f.write("--------------------------------------------------------------------\n")
            f.write("\n")
            f.write("GENERADOR GDB, SHP i DBF:\n")
            f.write("-------------------------\n")
            f.write(f"NomMuni:                {self.municipi_name}\n")
            f.write(f"IdMuni:                 {str(self.municipi_id)}\n")
            f.write(f"Superficie (CDT):       {self.municipi_superficie_cdt}\n")
            f.write(f"Extensio MM (geo):      {self.x_min}, {self.x_max}, {self.y_min}, {self.y_max}\n")
            f.write(f"ValidDe(CDT):           {self.municipi_valid_de}\n")
            f.write(f"DataAlta BMMC:          {self.data_alta}\n")
            f.write(f"Codi INE:               {self.municipi_codi_ine}\n")
            f.write(f"IdLinia (internes):     {str(self.municipi_lines)}\n")
            f.write(f"IdLinia de la costa:    {self.municipi_coast_line}\n")
            f.write(f"Carpeta shp, dbf i xml: {self.output_directory_name}\n")
            f.write("Shp i dbf generats:\n")
            for layer_name in self.entities_list:
                if 'taula' in layer_name or 'full' in layer_name:
                    layer_format = 'dbf'
                else:
                    layer_format = 'shp'
                new_layer_name = f'mapa-municipal-{self.municipi_normalized_name}-{layer_name}-{self.municipi_valid_de}.{layer_format}\n'
                f.write(f"  - {new_layer_name}")

    def set_polygon_info(self):
        """  """
        # Municipi Area
        self.municipi_superficie_cdt = self.generador_mmc_polygon.return_superficie_cdt()
        # Municipi Bounding Box
        self.x_min, self.x_max, self.y_min, self.y_max = self.generador_mmc_polygon.return_bounding_box()

    def export_data(self):
        """ """
        # Set output paths and layer or table names
        output_points_layer = f'mapa-municipal-{self.municipi_normalized_name}-fita-{self.municipi_valid_de}.shp'
        output_lines_layer = f'mapa-municipal-{self.municipi_normalized_name}-liniaterme-{self.municipi_valid_de}.shp'
        output_polygon_layer = f'mapa-municipal-{self.municipi_normalized_name}-poligon-{self.municipi_valid_de}.shp'
        output_lines_table = f'mapa-municipal-{self.municipi_normalized_name}-liniatermetaula-{self.municipi_valid_de}.dbf'
        output_coast_line_layer = f'mapa-municipal-{self.municipi_normalized_name}-liniacosta-{self.municipi_valid_de}.shp'
        output_coast_line_table = f'mapa-municipal-{self.municipi_normalized_name}-liniacostataula-{self.municipi_valid_de}.dbf'
        output_coast_line_full = f'mapa-municipal-{self.municipi_normalized_name}-tallfullbt5m-{self.municipi_valid_de}.dbf'
        # Export the data
        QgsVectorFileWriter.writeAsVectorFormat(self.work_point_layer, os.path.join(self.output_subdirectory_path, output_points_layer),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.work_line_layer,
                                                os.path.join(self.output_subdirectory_path, output_lines_layer),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.work_polygon_layer,
                                                os.path.join(self.output_subdirectory_path, output_polygon_layer),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.work_lines_table,
                                                os.path.join(self.output_subdirectory_path, output_lines_table),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.work_coast_line_layer,
                                                os.path.join(self.output_subdirectory_path, output_coast_line_layer),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.work_coast_line_table,
                                                os.path.join(self.output_subdirectory_path, output_coast_line_table),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        QgsVectorFileWriter.writeAsVectorFormat(self.work_coast_line_full,
                                                os.path.join(self.output_subdirectory_path, output_coast_line_full),
                                                'utf-8', self.crs, 'ESRI Shapefile')


class GeneradorMMCFites(GeneradorMMCLayers):

    def __init__(self, municipi_id, data_alta, fites_layer, dict_valid_de):
        GeneradorMMC.__init__(self, municipi_id, data_alta)
        self.work_point_layer = fites_layer
        self.dict_valid_de = dict_valid_de

    def generate_fites_layer(self):
        """ Main entry point """
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
        self.work_point_layer.dataProvider().deleteAttributes(delete_fields_list)
        self.work_point_layer.updateFields()

    def add_fields(self):
        """ Add necessary fields """
        # Set new fields
        # TODO funcion que retorne los campos comunes, idlinia, validde, valida, etc.
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
        self.work_point_layer.dataProvider().addAttributes(new_fields_list)
        self.work_point_layer.updateFields()

    def fill_fields(self):
        """ Fill the layer's fields """
        self.pg_adt.connect()
        fita_mem_layer = self.pg_adt.get_layer('v_fita_mem', 'id_fita')

        self.work_point_layer.startEditing()
        for point in self.work_point_layer.getFeatures():
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
            if point_monumentat:
                point['Monument'] = 'S'
            else:
                point['Monument'] = 'N'

            self.work_point_layer.updateFeature(point)

        self.work_point_layer.commitChanges()

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


class GeneradorMMCLines(GeneradorMMCLayers):

    def __init__(self, municipi_id, data_alta, lines_layer, dict_valid_de, coast):
        GeneradorMMC.__init__(self, municipi_id, data_alta, coast)
        self.work_line_layer = lines_layer
        self.temp_line_table = QgsVectorLayer('LineString', 'Line_table', 'memory')
        self.dict_valid_de = dict_valid_de

    def generate_lines_layer(self):
        """  """
        self.add_fields('layer')
        self.fill_fields_layer()
        self.delete_fields()

    def generate_lines_table(self):
        """  """
        self.add_fields('table')
        self.fill_fields_table()
        self.export_table()

        lines_table = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_LiniesTaula.dbf'))
        return lines_table

    def delete_fields(self):
        """  """
        delete_fields_list = list((0, 1))
        self.work_line_layer.dataProvider().deleteAttributes(delete_fields_list)
        self.work_line_layer.updateFields()

    def add_fields(self, entity):
        """  """
        # Set new fields
        id_linia_field = QgsField(name='IdLinia', type=QVariant.String, typeName='text', len=4)
        name_municipi_1_field = QgsField(name='NomTerme1', type=QVariant.String, typeName='text', len=100)
        name_municipi_2_field = QgsField(name='NomTerme2', type=QVariant.String, typeName='text', len=100)
        tipus_ua_field = QgsField(name='TipusUA', type=QVariant.String, typeName='text', len=17)
        limit_prov_field = QgsField(name='LimitProvi', type=QVariant.String, typeName='text', len=1)
        limit_vegue_field = QgsField(name='LimitVegue', type=QVariant.String, typeName='text', len=1)
        tipus_linia_field = QgsField(name='TipusLinia', type=QVariant.String, typeName='text', len=8)
        valid_de_field = QgsField(name='ValidDe', type=QVariant.String, typeName='text', len=8)
        valid_a_field = QgsField(name='ValidA', type=QVariant.String, typeName='text', len=8)
        data_alta_field = QgsField(name='DataAlta', type=QVariant.String, typeName='text', len=12)
        data_baixa_field = QgsField(name='DataBaixa', type=QVariant.String, typeName='text', len=12)
        codi_muni_field = QgsField(name='CodiMuni', type=QVariant.String, typeName='text', len=6)

        if entity == 'layer':
            new_fields_list = [id_linia_field, name_municipi_1_field, name_municipi_2_field, tipus_ua_field, limit_prov_field,
                               limit_vegue_field, tipus_linia_field, valid_de_field, valid_a_field, data_alta_field,
                               data_baixa_field]
            self.work_line_layer.dataProvider().addAttributes(new_fields_list)
            self.work_line_layer.updateFields()
        elif entity == 'table':
            new_fields_list = [id_linia_field, codi_muni_field]
            self.temp_line_table.dataProvider().addAttributes(new_fields_list)
            self.temp_line_table.updateFields()

    def fill_fields_layer(self):
        """  """
        self.work_line_layer.startEditing()
        for line in self.work_line_layer.getFeatures():
            line_id = line['id_linia']
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]
            # Get the Tipus UA type
            tipus_ua = line_data['TIPUSUA'][0]
            if tipus_ua == 'M':
                line['TipusUA'] = 'Municipi'
            elif tipus_ua == 'C':
                line['TipusUA'] = 'Comarca'
            elif tipus_ua == 'A':
                line['TipusUA'] = 'Comunitat Autònoma'
            elif tipus_ua == 'E':
                line['TipusUA'] = 'Estat'
            elif tipus_ua == 'I':
                line['TipusUA'] = 'Inframunicipal'
            # Get the Limit Vegue type
            limit_vegue = line_data['LIMVEGUE'][0]
            if limit_vegue == 'verdadero':
                line['LimitVegue'] = 'S'
            else:
                line['LimitVegue'] = 'N'
            # Get the tipus Linia type
            tipus_linia = line_data['TIPUSREG']
            if tipus_linia == 'internes':
                line['TipusLinia'] = 'MMC'
            else:
                line['TipusLinia'] = 'Exterior'
            # Non dependant fields
            line['IdLinia'] = line_id
            line['NomTerme1'] = str(line_data['NOMMUNI1'][0])
            line['NomTerme2'] = str(line_data['NOMMUNI2'][0])
            line['LimitProvi'] = str(line_data['LIMPROV'][0])
            line['ValidDe'] = self.dict_valid_de[line['id_linia']]
            line['DataAlta'] = self.data_alta

            self.work_line_layer.updateFeature(line)

        self.work_line_layer.commitChanges()

    def fill_fields_table(self):
        """  """
        self.temp_line_table.startEditing()
        for line in self.work_line_layer.getFeatures():
            line_id = line['IdLinia']
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromWkt('LineString()'))
            feature.setAttributes([line_id, self.municipi_codi_ine])
            self.temp_line_table.dataProvider().addFeatures([feature])

        self.temp_line_table.commitChanges()

    def export_table(self):
        """

        PyQGIS is not able to manage and export a standalone DBF file, so the working way is exporting the table as shapefile
        and then deleting all the associated files except the DBF one.
        """
        # Export the shapefile
        QgsVectorFileWriter.writeAsVectorFormat(self.temp_line_table,
                                                os.path.join(GENERADOR_WORK_DIR, 'MM_LiniesTaula.shp'),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        #  Delete the useless files
        for rm_format in ('.shp', '.shx', '.prj', '.cpg'):
            os.remove(os.path.join(GENERADOR_WORK_DIR, f'MM_LiniesTaula{rm_format}'))


class GeneradorMMCPolygon(GeneradorMMCLayers):

    def __init__(self, municipi_id, data_alta, polygon_layer):
        GeneradorMMC.__init__(self, municipi_id, data_alta)
        self.work_polygon_layer = polygon_layer

    def generate_polygon_layer(self):
        """ Main entry point """
        self.add_fields()
        self.fill_fields()
        self.delete_fields()

    def delete_fields(self):
        """  """
        self.work_polygon_layer.dataProvider().deleteAttributes([0])
        self.work_polygon_layer.updateFields()

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
        self.work_polygon_layer.dataProvider().addAttributes(new_fields_list)
        self.work_polygon_layer.updateFields()

    def fill_fields(self):
        """  """
        self.work_polygon_layer.startEditing()
        for polygon in self.work_polygon_layer.getFeatures():
            polygon['CodiMuni'] = self.municipi_codi_ine
            polygon['AreaMunMMC'] = polygon['Sup_CDT']
            polygon['NomMuni'] = str(self.municipi_name)
            polygon['ValidDe'] = self.municipi_valid_de
            polygon['DataAlta'] = self.data_alta
            self.work_polygon_layer.updateFeature(polygon)

        self.work_polygon_layer.commitChanges()

    def return_superficie_cdt(self):
        """  """
        superficie_cdt = ''
        for polygon in self.work_polygon_layer.getFeatures():
            superficie_cdt = polygon['AreaMunMMC']

        return superficie_cdt

    def return_bounding_box(self):
        """  """
        self.work_polygon_layer.selectAll()
        bounding_box_xy = self.work_polygon_layer.boundingBoxOfSelected()
        # Transform from X,Y to Lat, Long
        tr = QgsCoordinateTransform(self.crs, self.crs_geo, None)
        bounding_box = tr.transformBoundingBox(bounding_box_xy)
        # Get coordinates and round them
        y_min = round(bounding_box.yMinimum(), 9)
        y_max = round(bounding_box.yMaximum(), 9)
        x_min = round(bounding_box.xMinimum(), 9)
        x_max = round(bounding_box.xMaximum(), 9)

        return x_min, x_max, y_min, y_max


class GeneradorMMCCosta(GeneradorMMCLayers):

    def __init__(self, municipi_id, data_alta, lines_layer, dict_valid_de, coast):
        GeneradorMMC.__init__(self, municipi_id, data_alta, coast)
        self.coast_line_id = None
        self.work_lines_layer = lines_layer
        # Es important indicar el crs al crear la capa, si no la geometria no es veu correctament
        self.temp_coast_line_layer = QgsVectorLayer('LineString?crs=epsg:25831', 'Coast_line', 'memory')
        self.temp_coast_line_table = QgsVectorLayer('LineString', 'Coast_line_table', 'memory')
        self.temp_coast_full_table = QgsVectorLayer('LineString', 'Coast_full_table', 'memory')
        self.dict_valid_de = dict_valid_de

    def generate_coast_line_layer(self):
        """  """
        self.add_fields('layer')
        if self.coast:
            self.export_coast_line_layer()
        self.export_layer()

        coast_line_layer = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_LiniaCosta.shp'))
        return coast_line_layer

    def generate_coast_line_table(self):
        """  """
        self.add_fields('table')
        if self.coast:
            self.fill_fields_table()
        self.export_table('table')

        coast_line_table = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_LiniaCostaTaula.dbf'))
        return coast_line_table

    def generate_coast_full_bt5m_table(self):
        """  """
        self.add_fields('full')
        if self.coast:
            self.fill_fields_full_table()
        self.export_table('full')

        coast_line_full = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_FullBT5MCosta.dbf'))
        return coast_line_full

    def add_fields(self, entity):
        """  """
        # Set new fields
        id_linia_field = QgsField(name='IdLinia', type=QVariant.String, typeName='text', len=4)
        name_municipi_1_field = QgsField(name='NomTerme1', type=QVariant.String, typeName='text', len=100)
        valid_de_field = QgsField(name='ValidDe', type=QVariant.String, typeName='text', len=8)
        valid_a_field = QgsField(name='ValidA', type=QVariant.String, typeName='text', len=8)
        data_alta_field = QgsField(name='DataAlta', type=QVariant.String, typeName='text', len=12)
        data_baixa_field = QgsField(name='DataBaixa', type=QVariant.String, typeName='text', len=12)
        codi_muni_field = QgsField(name='CodiMuni', type=QVariant.String, typeName='text', len=6)
        # Full BT5M fields
        id_full_field = QgsField(name='IdFullBT5M', type=QVariant.String, typeName='text', len=6)
        versio_field = QgsField(name='Versio', type=QVariant.String, typeName='text', len=5)
        revisio_field = QgsField(name='Revisio', type=QVariant.String, typeName='text', len=2)
        correccio_field = QgsField(name='Correccio', type=QVariant.String, typeName='text', len=1)

        if entity == 'layer':
            new_fields_list = [id_linia_field, name_municipi_1_field, valid_de_field, valid_a_field, data_alta_field,
                               data_baixa_field]
            self.temp_coast_line_layer.dataProvider().addAttributes(new_fields_list)
            self.temp_coast_line_layer.updateFields()
        elif entity == 'table':
            new_fields_list = [id_linia_field, codi_muni_field]
            self.temp_coast_line_table.dataProvider().addAttributes(new_fields_list)
            self.temp_coast_line_table.updateFields()
        elif entity == 'full':
            new_fields_list = [id_full_field, versio_field, revisio_field, correccio_field, id_linia_field]
            self.temp_coast_full_table.dataProvider().addAttributes(new_fields_list)
            self.temp_coast_full_table.updateFields()

    def export_coast_line_layer(self):
        """  """
        for line in self.work_lines_layer.getFeatures():
            line_id = line['IdLinia']
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == int(line_id))]
            if line_data['LIMCOSTA'] == 'S':
                self.coast_line_id = line_id
                coast_line_geom = line.geometry()
                self.work_lines_layer.startEditing()
                self.work_lines_layer.deleteFeature(line.id())   # Delete the coast line from the lines layer
                self.work_lines_layer.commitChanges()

        self.temp_coast_line_layer.startEditing()
        coast_line = QgsFeature()
        coast_line.setGeometry(coast_line_geom)
        coast_line.setAttributes([self.coast_line_id, str(self.municipi_name), self.dict_valid_de[int(self.coast_line_id)], '',
                                  self.data_alta, ''])
        self.temp_coast_line_layer.dataProvider().addFeatures([coast_line])
        self.temp_coast_line_layer.commitChanges()

    def fill_fields_table(self):
        """  """
        self.temp_coast_line_table.startEditing()
        for line in self.temp_coast_line_layer.getFeatures():
            line_id = line['IdLinia']
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromWkt('LineString()'))
            feature.setAttributes([line_id, self.municipi_codi_ine])
            self.temp_coast_line_table.dataProvider().addFeatures([feature])

        self.temp_coast_line_table.commitChanges()

    def fill_fields_full_table(self):
        """  """
        with open(COAST_TXT, 'r') as f:
            fulls = f.readlines()
        self.temp_coast_full_table.startEditing()
        for full in fulls:
            full = full.replace("\n", "")   # Remove the new line character
            id_full = full[11:17]
            versio = full[5:10]
            revisio = full[-3:-1]
            correccio = full[-1]
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromWkt('LineString()'))
            feature.setAttributes([id_full, versio, revisio, correccio, self.coast_line_id])
            self.temp_coast_full_table.dataProvider().addFeatures([feature])

        self.temp_coast_full_table.commitChanges()

    def export_layer(self):
        """  """
        QgsVectorFileWriter.writeAsVectorFormat(self.temp_coast_line_layer,
                                                os.path.join(GENERADOR_WORK_DIR, 'MM_LiniaCosta.shp'),
                                                'utf-8', self.crs, 'ESRI Shapefile')

    def export_table(self, table_type):
        """

        PyQGIS is not able to manage and export a standalone DBF file, so the working way is exporting the table as shapefile
        and then deleting all the associated files except the DBF one.
        """
        if table_type == 'table':
            table_name = 'MM_LiniaCostaTaula'
            table = self.temp_coast_line_table
        elif table_type == 'full':
            table_name = 'MM_FullBT5MCosta'
            table = self.temp_coast_full_table
        # Export the shapefile
        QgsVectorFileWriter.writeAsVectorFormat(table,
                                                os.path.join(GENERADOR_WORK_DIR, f'{table_name}.shp'),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        #  Delete the useless files
        for rm_format in ('.shp', '.shx', '.prj', '.cpg'):
            os.remove(os.path.join(GENERADOR_WORK_DIR, f'{table_name}{rm_format}'))


class GeneradorMMCChecker(GeneradorMMC):
    def __init__(self, municipi_id):
        GeneradorMMC.__init__(self, municipi_id)

    def get_municipi_normalized_name(self):
        """ Get the municipi's normalized name, without accent marks or special characters """
        muni_data = self.arr_name_municipis[np.where(self.arr_name_municipis['id_area'] == self.municipi_id)]
        muni_norm_name = muni_data['nom_muni_norm'][0]

        return muni_norm_name

    def get_municipi_codi_ine(self):
        """  """
        muni_data = self.arr_name_municipis[np.where(self.arr_name_municipis['id_area'] == self.municipi_id)]
        codi_ine = muni_data['codi_ine_muni'][0].strip('"\'')

        return codi_ine

    def check_mm_exists(self):
        """  """
        self.pg_adt.connect()
        mapa_muni_table = self.pg_adt.get_table('mapa_muni_icc')
        mapa_muni_table.selectByExpression(f'"codi_muni"=\'{self.municipi_codi_ine}\' and "vig_mm" is True',
                                           QgsVectorLayer.SetSelection)
        count = mapa_muni_table.selectedFeatureCount()
        if count == 0:
            e_box = QMessageBox()
            e_box.setIcon(QMessageBox.Critical)
            e_box.setText("El municipi no té Mapa Municipal considerat")
            e_box.exec_()
            return False
        else:
            return True

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
        layers_missing = []
        for layer in ('MM_Fites.shp', 'MM_Linies.shp', 'MM_Poligons.shp'):
            if layer not in shapefiles_list:
                layers_missing.append(layer)

        if len(layers_missing) == 0:
            return True
        else:
            e_box = QMessageBox()
            e_box.setIcon(QMessageBox.Warning)
            if len(layers_missing) == 1:
                e_box.setText(f"No existeix la capa {layer} a la carpeta de Shapefiles del municipi")
            elif len(layers_missing) > 1:
                e_box.setText("No existeixen les següents capes a la carpeta de Shapefiles del municipi")
                for layer_missing in layers_missing:
                    e_box.setText(f"    - {layer_missing}")
            e_box.exec_()
            return False


class GeneradorMMCMetadataTable(GeneradorMMC):

    def __init__(self, municipi_id, data_alta):
        GeneradorMMC.__init__(self, municipi_id, data_alta)
        if os.path.exists(self.municipi_metadata_table):
            os.remove(self.municipi_metadata_table)
        else:
            self.municipi_metadata_table = QgsVectorLayer('LineString', 'Coast_full_table', 'memory')

    def generate_metadata_table(self):
        """  """
        self.add_fields()
        self.fill_fields()

    def add_fields(self):
        """  """
        id_linia_field = QgsField(name='IdLinia', type=QVariant.String, typeName='text', len=4)
        name_municipi_1_field = QgsField(name='NomMuni1', type=QVariant.String, typeName='text', len=100)
        name_municipi_2_field = QgsField(name='NomMuni2', type=QVariant.String, typeName='text', len=100)
        tipus_ua_field = QgsField(name='TipusUA', type=QVariant.String, typeName='text', len=17)
        tipus_reg_field = QgsField(name='TipusReg', type=QVariant.String, typeName='text', len=17)
        limit_prov_field = QgsField(name='LimProv', type=QVariant.String, typeName='text', len=1)
        id_municipi_1_field = QgsField(name='IdMuni1', type=QVariant.String, typeName='text', len=4)
        id_municipi_2_field = QgsField(name='IdMuni2', type=QVariant.String, typeName='text', len=4)
        data_acta_h_field = QgsField(name='DataActaH', type=QVariant.String, typeName='text', len=8)
        id_acta_field = QgsField(name='IdActa', type=QVariant.String, typeName='text', len=10)
        data_rep_field = QgsField(name='DataRep', type=QVariant.String, typeName='text', len=8)
        tip_rep_field = QgsField(name='TipusRep', type=QVariant.String, typeName='text', len=17)
        abast_rep_field = QgsField(name='AbastRep', type=QVariant.String, typeName='text', len=17)
        org_rep_field = QgsField(name='OrgRep', type=QVariant.String, typeName='text', len=50)
        fi_rep_field = QgsField(name='FiRep', type=QVariant.String, typeName='text', len=17)
        data_dogc_field = QgsField(name='DataDOGC', type=QVariant.String, typeName='text', len=8)
        data_pub_dogc_field = QgsField(name='DataPubDOGC', type=QVariant.String, typeName='text', len=8)
        tipus_dogc_field = QgsField(name='TipusDOGC', type=QVariant.String, typeName='text', len=17)
        tit_dogc_field = QgsField(name='TITDOGC', type=QVariant.String, typeName='text', len=100)
        esm_dogc_field = QgsField(name='EsmDOGC', type=QVariant.String, typeName='text', len=10)
        tip_dogc_field = QgsField(name='TipPubDOGC', type=QVariant.String, typeName='text', len=10)
        vig_dogc_field = QgsField(name='VigPubDOGC', type=QVariant.String, typeName='text', len=10)
        data_rec_field = QgsField(name='DataActaRec', type=QVariant.String, typeName='text', len=8)
        tipus_rec_field = QgsField(name='TipusActaRec', type=QVariant.String, typeName='text', len=17)
        vig_rec_field = QgsField(name='VigActaRec', type=QVariant.String, typeName='text', len=10)
        vig_aterm_field = QgsField(name='VigActaAterm', type=QVariant.String, typeName='text', len=10)
        data_mtt_field = QgsField(name='DataMTT', type=QVariant.String, typeName='text', len=8)
        abast_mtt_field = QgsField(name='AbastMTT', type=QVariant.String, typeName='text', len=8)
        vig_mtt_field = QgsField(name='VigMTT', type=QVariant.String, typeName='text', len=8)
        data_mmc_field = QgsField(name='DataMMC', type=QVariant.String, typeName='text', len=8)
        data_cdt_field = QgsField(name='DataCDT', type=QVariant.String, typeName='text', len=8)

        new_fields_list = [id_linia_field, name_municipi_1_field, name_municipi_2_field, tipus_ua_field, tipus_reg_field,
                           limit_prov_field, id_municipi_1_field, id_municipi_2_field, data_acta_h_field, data_rep_field,
                           tip_rep_field, abast_rep_field, org_rep_field, fi_rep_field, id_acta_field, data_dogc_field, data_pub_dogc_field,
                           tipus_dogc_field, tit_dogc_field, esm_dogc_field, tip_dogc_field, vig_dogc_field, data_rec_field,
                           tipus_rec_field, vig_rec_field, vig_aterm_field, data_mtt_field, abast_mtt_field, vig_mtt_field, data_mmc_field,
                           data_cdt_field
                           ]
        self.municipi_metadata_table.dataProvider().addAttributes(new_fields_list)
        self.municipi_metadata_table.updateFields()

    def fill_fields(self):
        """  """
        self.municipi_metadata_table.startEditing()
        for line_id in self.municipi_lines:
            nom_muni1 = self.municipis_names_lines[line_id][0]
            nom_muni2 = self.municipis_names_lines[line_id][1]
            # Data from the line data dict related to the line itself
            line_data = self.get_line_data(line_id)
            tipus_ua = line_data['TIPUSUA'][0]
            lim_prov = line_data['LIMPROV'][0]
            tipus_reg = line_data['TIPUSREG'][0]
            codi_muni1 = str(line_data['CODIMUNI1'][0])
            codi_muni2 = str(line_data['CODIMUNI2'][0])

            '''
            feature = QgsFeature()
            feature.setGeometry(QgsGeometry.fromWkt('LineString()'))
            feature.setAttributes([line_id, self.municipi_codi_ine])
            self.municipi_metadata_table.dataProvider().addFeatures([feature])
            '''

        self.municipi_metadata_table.commitChanges()

    def get_line_data(self, line_id):
        """  """
        line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]

        return line_data

    def get_acta_h_data(self, line_id):
        """  """
        pass

    def get_rep_data(self, line_id):
        """  """
        pass

    def get_dogc_data(self, line_id):
        """  """
        pass

    def get_rec_data(self, line_id):
        """  """
        pass

    def get_mtt_data(self, line_id):
        """  """
        pass

    def get_mm_data(self, line_id):
        """  """
        pass


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


# REMOVE TEMP FILES
def remove_generador_temp_files():
    """ Remove temp files """
    # Sembla ser que hi ha un bug que impedeix esborrar els arxius .shp i .dbf si no es tanca i es torna
    # a obrir la finestra del plugin
    temp_list = os.listdir(GENERADOR_WORK_DIR)
    for temp in temp_list:
        if temp in TEMP_ENTITIES:
            QgsVectorFileWriter.deleteShapeFile(os.path.join(GENERADOR_WORK_DIR, temp))

    info_box = QMessageBox()
    info_box.setText("Arxius temporals esborrats")
    info_box.exec_()

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
import xml.etree.ElementTree as ET

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


# TODO comment correctly


class GeneradorMMC(object):
    """ MMC Generation class """

    def __init__(self,
                 municipality_id,
                 data_alta=None,
                 coast=False):
        """
        Constructor

        :param municipality_id: ID of the municipality
        :type municipality_id: str

        :param data_alta: Update date
        :type data_alta: str

        :param coast: Indicates if the municipality has coast or not
        :type coast: bool
        """
        # Initialize instance attributes
        # Common
        self.arr_nom_municipalities = np.genfromtxt(DIC_NOM_MUNICIPIS, dtype=None, encoding=None, delimiter=';', names=True)
        self.arr_lines_data = np.genfromtxt(DIC_LINES, dtype=None, encoding=None, delimiter=';', names=True)
        self.crs = QgsCoordinateReferenceSystem("EPSG:25831")
        self.crs_geo = QgsCoordinateReferenceSystem("EPSG:4258")
        self.entities_list = ('fita', 'liniacosta', 'liniacostaula', 'liniaterme', 'liniatermetaula', 'poligon',
                              'tallfullbt5m')
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        # ###
        # Input dependant that don't need data from the layers
        self.municipality_id = int(municipality_id)
        self.data_alta = data_alta
        self.coast = coast
        self.municipality_name = self.get_municipality_name()
        self.municipality_normalized_name = self.get_municipality_normalized_name()
        self.municipality_nomens = self.get_municipality_nomens()
        self.municipality_codi_ine = self.get_municipality_codi_ine()
        self.municipality_valid_de = self.get_municipality_valid_de()
        self.metadata_table_name = f'{self.municipality_id}_Taula_espec_C4'
        self.metadata_table_path = os.path.join(GENERADOR_TAULES_ESPEC, f'{self.metadata_table_name}.dbf')
        self.municipality_metadata_table = self.get_municipality_metadata_table()   # Can be None
        # ###
        # Input dependant that need data from the line layer
        # Paths
        self.municipality_input_dir = os.path.join(GENERADOR_INPUT_DIR, self.municipality_normalized_name)
        self.shapefiles_input_dir = os.path.join(self.municipality_input_dir, SHAPEFILES_PATH)
        self.output_directory_name = f'mapa-municipal-{self.municipality_normalized_name}-{self.municipality_valid_de}'
        self.output_directory_path = os.path.join(GENERADOR_OUTPUT_DIR, self.output_directory_name)
        self.output_subdirectory_path = os.path.join(self.output_directory_path, self.output_directory_name)
        self.report_path = os.path.join(self.output_directory_path, f'{str(municipality_id)}_Report.txt')
        # Input line layer as Vector Layer for getting some data related to the lines ID
        self.input_line_layer = QgsVectorLayer(os.path.join(self.shapefiles_input_dir, 'MM_Linies.shp'))
        # Get a list with all the lines ID
        self.municipality_lines = self.get_municipality_lines(self.input_line_layer)
        if not self.coast:
            self.municipality_coast_line = 'Aquest MM no te linia de costa.'
        else:
            self.municipality_coast_line = self.get_municipality_coast_line(self.input_line_layer)
        # Get a dictionary with all the ValidDe dates per line
        self.dict_valid_de = self.get_lines_valid_de(self.input_line_layer)
        # Get a dictionary with the municipalities names per line
        self.municipalities_names_lines = self.get_municipalities_names_line()

    # #######################
    # Setters & Getters
    def get_municipality_name(self):
        """
        Get the name of the input municipality

        :return: muni_name: Name of the municipality
        :rtype: str
        """
        muni_data = self.arr_nom_municipalities[np.where(self.arr_nom_municipalities['id_area'] == f'"{self.municipality_id}"')]
        muni_name = muni_data['nom_muni'][0]

        return muni_name

    def get_municipality_normalized_name(self):
        """
        Get the municipality's normalized name, without accent marks or special characters

        :return: muni_norm_name: Normalized name of the municipality
        :rtype: str
        """
        muni_data = self.arr_nom_municipalities[np.where(self.arr_nom_municipalities['id_area'] == f'"{self.municipality_id}"')]
        muni_norm_name = muni_data['nom_muni_norm'][0]

        return muni_norm_name

    def get_municipality_nomens(self):
        """
        Get how to name the input municipality in the metadata

        :return: muni_nomens: Way to say the municipality name
        :rtype: str
        """
        muni_data = self.arr_nom_municipalities[np.where(self.arr_nom_municipalities['id_area'] == f'"{self.municipality_id}"')]
        muni_nomens = muni_data['nomens'][0]

        return muni_nomens

    def get_municipality_lines(self, lines_layer):
        """
        Get all the municipal boundary lines that make the input municipality

        :param lines_layer: Layer of the municipality's boundary lines
        :type lines_layer: QgsVectorLayer

        :return: line_list: List with the ID of the lines
        :rtype: tuple
        """
        line_list = []
        for line in lines_layer.getFeatures():
            line_id = line['id_linia']
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]
            if line_data['LIMCOSTA'] == 'N':
                line_list.append(line_id)

        return line_list

    def get_municipality_coast_line(self, lines_layer):
        """
        Get the municipality coast line, if exists

        :param lines_layer: Layer of the municipality's boundary lines
        :type lines_layer: QgsVectorLayer

        :return coast_line_id: ID of the coast line
        :rtype: str
        """
        coast_line_id = ''
        for line in lines_layer.getFeatures():
            line_id = line['id_linia']
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]
            if line_data['LIMCOSTA'] == 'S':
                coast_line_id = line_id

        return coast_line_id

    def get_lines_valid_de(self, lines_layer):
        """
        Get the ValidDe date from every line that conform the municipality's boundary. Each date is equal to the
        CDT date from the memories_treb_top table

        :param lines_layer: Layer of the municipality's boundary lines
        :type lines_layer: QgsVectorLayer

        :return: dict_valid_de: Dictionary with the ValidDe date of every line
        :rtype: dict
        """
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

    def get_municipality_valid_de(self):
        """
        Get the municipality Valid De from the CDT date

        :return: municipality_cdt_str: Date of the Valid De from the CDT date
        :rtype: str
        """
        mapa_muni_table = self.pg_adt.get_table('mapa_muni_icc')
        mapa_muni_table.selectByExpression(f'"codi_muni"=\'{self.municipality_codi_ine}\' and "vig_mm" is True',
                                           QgsVectorLayer.SetSelection)
        municipality_cdt_str = ''
        for feature in mapa_muni_table.getSelectedFeatures():
            municipality_cdt = feature['data_con_cdt']
            municipality_cdt_str = municipality_cdt.toString('yyyyMMdd')

        return municipality_cdt_str

    def get_municipality_codi_ine(self):
        """
        Get the municipality INE ID

        :return codi_ine: INE ID of the municipality
        :rtype: str
        """
        muni_data = self.arr_nom_municipalities[np.where(self.arr_nom_municipalities['id_area'] == f'"{self.municipality_id}"')]
        codi_ine = muni_data['codi_ine_muni'][0].strip('"\'')

        return codi_ine

    def get_municipality_metadata_table(self):
        """
        Get the path of the municipality's metadata table

        :return: layer of the metadata table
        :rtype: QgsVectorLayer
        """
        if os.path.exists(self.metadata_table_path):
            return QgsVectorLayer(self.metadata_table_path)
        else:
            return ''

    def get_municipalities_names_line(self):
        """
        Get the pairs of the municipalities names that share every line that make the municipality

        :return: municipalities_names_line: list with the names of the municipalities that share a boundary line
        :rtype: tuple
        """
        municipalities_names_line = {}
        for line_id in self.municipality_lines:
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == int(line_id))]
            name_muni_1 = line_data['NOMMUNI1'][0]
            name_muni_2 = line_data['NOMMUNI2'][0]
            municipalities_names_line[line_id] = (name_muni_1, name_muni_2)

        return municipalities_names_line

    def open_report(self):
        """ Open the txt log report """
        if os.path.exists(self.report_path):
            os.startfile(self.report_path, 'open')
        else:
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setText("No existeix cap arxiu de report")
            box.exec_()
            return


class GeneradorMMCLayers(GeneradorMMC):

    def __init__(self,
                 municipality_id,
                 data_alta,
                 coast=False):
        """
        Constructor

        :param municipality_id: ID of the municipality
        :type municipality_id: str

        :param data_alta: Update date
        :type data_alta: str

        :param coast: Indicates if the municipality has coast or not
        :type coast: bool
        """
        GeneradorMMC.__init__(self, municipality_id, data_alta, coast)
        # Work layers paths
        self.work_point_layer = None
        self.work_line_layer = None
        self.work_polygon_layer = None
        self.work_lines_table = None
        self.work_coast_line_layer = None
        self.work_coast_line_table = None
        self.work_coast_line_full = None
        self.municipality_superficie_cdt = None
        # Bounding box coordinates
        self.y_min = None
        self.y_max = None
        self.x_min = None
        self.x_max = None
        # Instances
        self.generador_mmc_polygon = None

    def generate_mmc_layers(self):
        """ Main entry point. Here is where is done all the MMC layer and metadata generation """
        # ########################
        # SET DATA
        # Copy data to work directory
        self.copy_data_to_work()
        # Set the layers paths
        self.work_point_layer, self.work_line_layer, self.work_polygon_layer = self.set_layers_paths()

        # ########################
        # LAYERS GENERATION PROCESS
        # Lines
        generador_mmc_lines = GeneradorMMCLines(self.municipality_id, self.data_alta, self.work_line_layer,
                                                self.dict_valid_de, self.coast)
        generador_mmc_lines.generate_lines_layer()   # Layer
        self.work_lines_table = generador_mmc_lines.generate_lines_table()   # Table
        # Fites
        generador_mmc_fites = GeneradorMMCFites(self.municipality_id, self.data_alta, self.work_point_layer,
                                                self.dict_valid_de)
        generador_mmc_fites.generate_fites_layer()
        # Polygon
        self.generador_mmc_polygon = GeneradorMMCPolygon(self.municipality_id, self.data_alta, self.work_polygon_layer)
        self.generador_mmc_polygon.generate_polygon_layer()
        # Costa
        generador_mmc_costa = GeneradorMMCCosta(self.municipality_id, self.data_alta, self.work_line_layer,
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
        # Remove redundant cpg files
        self.remove_cpg_files()

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
        """
        Set the paths to the layers and directories to be managed

        :return: Points, lines and polygon layers of the municipalitye
        :rtype: QgsVectorLayer
        """
        points_layer = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_Fites.shp'))
        lines_layer = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_Linies.shp'))
        polygon_layer = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_Poligons.shp'))

        return points_layer, lines_layer, polygon_layer

    def make_output_directories(self):
        """ Create the export output directories if they don't exist """
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
        """ Write the log report with the necessary info """
        # Remove the report if it already exists
        if os.path.exists(self.report_path):
            os.remove(self.report_path)
        # Set the report info
        self.set_polygon_info()
        # Write the report
        with open(self.report_path, 'a+') as f:
            f.write("--------------------------------------------------------------------\n")
            f.write(f"REPORT DEL MM: {self.municipality_name} (considerat: {self.municipality_valid_de})\n")
            f.write("--------------------------------------------------------------------\n")
            f.write("\n")
            f.write("GENERADOR GDB, SHP i DBF:\n")
            f.write("-------------------------\n")
            f.write(f"NomMuni:                {self.municipality_name}\n")
            f.write(f"IdMuni:                 {self.municipality_id}\n")
            f.write(f"Superficie (CDT):       {self.municipality_superficie_cdt}\n")
            f.write(f"Extensio MM (geo):      {self.x_min}, {self.x_max}, {self.y_min}, {self.y_max}\n")
            f.write(f"ValidDe(CDT):           {self.municipality_valid_de}\n")
            f.write(f"DataAlta BMMC:          {self.data_alta}\n")
            f.write(f"Codi INE:               {self.municipality_codi_ine}\n")
            f.write(f"IdLinia (internes):     {str(self.municipality_lines)}\n")
            f.write(f"IdLinia de la costa:    {self.municipality_coast_line}\n")
            f.write(f"Carpeta shp, dbf i xml: {self.output_directory_name}\n")
            f.write("Shp i dbf generats:\n")
            for layer_name in self.entities_list:
                if 'taula' in layer_name or 'full' in layer_name:
                    layer_format = 'dbf'
                else:
                    layer_format = 'shp'
                new_layer_name = f'mapa-municipal-v1r0-{self.municipality_normalized_name}-{layer_name}-{self.municipality_valid_de}.{layer_format}\n'
                f.write(f"  - {new_layer_name}")

    def set_polygon_info(self):
        """
        Set some polygon information related to the municipality such as:
            - Superficie CDT - Area of the municipality validated by the CDT
            - Bounding Box - Bounding box of the municipality
         """
        # Municipi Area
        self.municipality_superficie_cdt = self.generador_mmc_polygon.return_superficie_cdt()
        # Municipi Bounding Box
        self.x_min, self.x_max, self.y_min, self.y_max = self.generador_mmc_polygon.return_bounding_box()

    def export_data(self):
        """ Export all the imported and managed data to the output directories """
        # Set output paths and layer or table names
        output_points_layer = f'mapa-municipal-v1r0-{self.municipality_normalized_name}-fita-{self.municipality_valid_de}.shp'
        output_lines_layer = f'mapa-municipal-v1r0-{self.municipality_normalized_name}-liniaterme-{self.municipality_valid_de}.shp'
        output_polygon_layer = f'mapa-municipal-v1r0-{self.municipality_normalized_name}-poligon-{self.municipality_valid_de}.shp'
        output_lines_table = f'mapa-municipal-v1r0-{self.municipality_normalized_name}-liniatermetaula-{self.municipality_valid_de}.shp'
        output_coast_line_layer = f'mapa-municipal-v1r0-{self.municipality_normalized_name}-liniacosta-{self.municipality_valid_de}.shp'
        output_coast_line_table = f'mapa-municipal-v1r0-{self.municipality_normalized_name}-liniacostataula-{self.municipality_valid_de}.shp'
        output_coast_line_full = f'mapa-municipal-v1r0-{self.municipality_normalized_name}-tallfullbt5m-{self.municipality_valid_de}.shp'
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

    def remove_cpg_files(self):
        """  """
        output_files = os.listdir(self.output_subdirectory_path)
        for file in output_files:
            if 'taula' in file or 'tall' in file:
                if file.endswith('.cpg'):
                    file_path = os.path.join(self.output_subdirectory_path, file)
                    os.remove(file_path)


class GeneradorMMCFites(GeneradorMMCLayers):

    def __init__(self,
                 municipality_id,
                 data_alta,
                 fites_layer,
                 dict_valid_de):
        """
        Constructor

        :param municipality_id: ID of the municipality
        :type municipality_id: str

        :param data_alta: Update date
        :type data_alta: str

        :param fites_layer: Points layer of the municipality
        :type fites_layer: QgsVectorLayer

        :return: dict_valid_de: Dictionary with the ValidDe date of every line
        :rtype: dict
        """
        GeneradorMMC.__init__(self, municipality_id, data_alta)
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
        id_u_fita_field = QgsField(name='IdUfita', type=QVariant.String, typeName='text', len=10)
        id_fita_field = QgsField(name='IdFita', type=QVariant.String, typeName='text', len=18)
        id_sector_field = QgsField(name='IdSector', type=QVariant.String, typeName='text', len=1)
        id_fita_r_field = QgsField(name='IdFitaR', type=QVariant.String, typeName='text', len=3)
        num_termes_field = QgsField(name='NumTermes', type=QVariant.String, typeName='text', len=3)
        monument_field = QgsField(name='Monument', type=QVariant.String, typeName='text', len=1)
        id_linia_field, valid_de_field, valid_a_field, data_alta_field, data_baixa_field = get_common_fields()
        new_fields_list = [id_u_fita_field, id_fita_field, id_sector_field, id_fita_r_field, num_termes_field,
                           monument_field, valid_de_field, valid_a_field, data_alta_field, data_baixa_field,
                           id_linia_field]
        self.work_point_layer.dataProvider().addAttributes(new_fields_list)
        self.work_point_layer.updateFields()

    def fill_fields(self):
        """ Fill the layer's fields """
        point_id_u_fita, point_id_fita, point_r_fita, point_sector, point_num_termes, point_monumentat = ('',) * 6
        fita_mem_layer = self.pg_adt.get_layer('v_fita_mem', 'id_fita')

        with edit(self.work_point_layer):
            for point in self.work_point_layer.getFeatures():
                point_id = point['id_punt']
                fita_mem_layer.selectByExpression(f'"id_punt"=\'{point_id}\'', QgsVectorLayer.SetSelection)
                for feature in fita_mem_layer.getSelectedFeatures():
                    point_id_u_fita = feature['id_u_fita']
                    point_id_fita = coordinates_to_id_fita(feature['point_x'], feature['point_y'])
                    point_r_fita = point_num_to_text(feature['num_fita'])
                    point_sector = feature['num_sector']
                    point_num_termes = feature['num_termes']
                    point_monumentat = feature['trobada']

                point['IdUFita'] = point_id_u_fita[:-2]
                point['IdFita'] = point_id_fita
                point['IdFitaR'] = point_r_fita
                point['IdSector'] = point_sector
                point['NumTermes'] = point_num_termes
                line_id_txt = line_id_2_txt(point['id_linia'])
                point['IdLinia'] = line_id_txt
                point['DataAlta'] = self.data_alta
                point['ValidDe'] = self.dict_valid_de[point['id_linia']]
                if point_monumentat:
                    point['Monument'] = 'S'
                else:
                    point['Monument'] = 'N'

                self.work_point_layer.updateFeature(point)


class GeneradorMMCLines(GeneradorMMCLayers):

    def __init__(self,
                 municipality_id,
                 data_alta,
                 lines_layer,
                 dict_valid_de,
                 coast):
        """
        Constructor

        :param municipality_id: ID of the municipality
        :type municipality_id: str

        :param data_alta: Update date
        :type data_alta: str

        :param lines_layer: Lines layer of the municipality
        :type lines_layer: QgsVectorLayer

        :param: dict_valid_de: Dictionary with the ValidDe date of every line
        :type dict_valid_de: dict

        :param coast: Indicates if the municipality has coast or not
        :type coast: bool
        """
        GeneradorMMC.__init__(self, municipality_id, data_alta, coast)
        self.work_line_layer = lines_layer
        self.temp_line_table = QgsVectorLayer('LineString', 'Line_table', 'memory')
        self.dict_valid_de = dict_valid_de

    def generate_lines_layer(self):
        """ Main entry point for generating the lines layer """
        self.add_fields('layer')
        self.fill_fields_layer()
        self.delete_fields()

    def generate_lines_table(self):
        """
        Main entry point for generating the lines table

        :return: lines_table: DBF attributes table of the lines layer
        :rtype: QgsVectorLayer
        """
        self.add_fields('table')
        self.fill_fields_table()
        self.export_table()

        lines_table = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_LiniesTaula.dbf'))
        return lines_table

    def delete_fields(self):
        """ Delete non necessary fields """
        delete_fields_list = list((0, 1))
        self.work_line_layer.dataProvider().deleteAttributes(delete_fields_list)
        self.work_line_layer.updateFields()

    def add_fields(self, entity):
        """ Add necessary fields """
        # Set new fields
        name_municipality_1_field = QgsField(name='NomTerme1', type=QVariant.String, typeName='text', len=100)
        name_municipality_2_field = QgsField(name='NomTerme2', type=QVariant.String, typeName='text', len=100)
        tipus_ua_field = QgsField(name='TipusUA', type=QVariant.String, typeName='text', len=17)
        limit_prov_field = QgsField(name='LimitProvi', type=QVariant.String, typeName='text', len=1)
        limit_vegue_field = QgsField(name='LimitVegue', type=QVariant.String, typeName='text', len=1)
        tipus_linia_field = QgsField(name='TipusLinia', type=QVariant.String, typeName='text', len=8)
        codi_muni_field = QgsField(name='CodiMuni', type=QVariant.String, typeName='text', len=6)
        id_linia_field, valid_de_field, valid_a_field, data_alta_field, data_baixa_field = get_common_fields()

        if entity == 'layer':
            new_fields_list = [id_linia_field, name_municipality_1_field, name_municipality_2_field, tipus_ua_field, limit_prov_field,
                               limit_vegue_field, tipus_linia_field, valid_de_field, valid_a_field, data_alta_field,
                               data_baixa_field]
            self.work_line_layer.dataProvider().addAttributes(new_fields_list)
            self.work_line_layer.updateFields()
        elif entity == 'table':
            new_fields_list = [id_linia_field, codi_muni_field]
            self.temp_line_table.dataProvider().addAttributes(new_fields_list)
            self.temp_line_table.updateFields()

    def fill_fields_layer(self):
        """ Fill the layer's new fields with necessary data """
        with edit(self.work_line_layer):
            for line in self.work_line_layer.getFeatures():
                line_id = line['id_linia']
                line_id_txt = line_id_2_txt(line_id)
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
                line['IdLinia'] = line_id_txt
                line['NomTerme1'] = str(line_data['NOMMUNI1'][0])
                line['NomTerme2'] = str(line_data['NOMMUNI2'][0])
                line['LimitProvi'] = str(line_data['LIMPROV'][0])
                line['ValidDe'] = self.dict_valid_de[line['id_linia']]
                line['DataAlta'] = self.data_alta

                self.work_line_layer.updateFeature(line)

    def fill_fields_table(self):
        """ Fill the table's new fields with the necessary data """
        with edit(self.temp_line_table):
            for line in self.work_line_layer.getFeatures():
                line_id = line['IdLinia']
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromWkt('LineString()'))
                feature.setAttributes([line_id, self.municipality_codi_ine])
                self.temp_line_table.dataProvider().addFeatures([feature])

    def export_table(self):
        """
        Export the lines table as a dbf file.

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

    def __init__(self,
                 municipality_id,
                 data_alta,
                 polygon_layer):
        """
        Constructor

        :param municipality_id: ID of the municipality
        :type municipality_id: str

        :param data_alta: Update date
        :type data_alta: str

        :param polygon_layer: Polygon layer of the municipality
        :type polygon_layer: QgsVectorLayer
        """
        GeneradorMMC.__init__(self, municipality_id, data_alta)
        self.work_polygon_layer = polygon_layer

    def generate_polygon_layer(self):
        """ Main entry point """
        self.add_fields()
        self.fill_fields()
        self.delete_fields()

    def delete_fields(self):
        """ Delete non necessary fields """
        self.work_polygon_layer.dataProvider().deleteAttributes([0])
        self.work_polygon_layer.updateFields()

    def add_fields(self):
        """ Add necessary fields """
        # Set new fields
        codi_muni_field = QgsField(name='CodiMuni', type=QVariant.String, typeName='text', len=6)
        area_muni_field = QgsField(name='AreaMunMMC', type=QVariant.String, typeName='text', len=8)
        name_muni_field = QgsField(name='NomMuni', type=QVariant.String, typeName='text', len=100)
        id_linia_field, valid_de_field, valid_a_field, data_alta_field, data_baixa_field = get_common_fields()
        new_fields_list = [codi_muni_field, area_muni_field, name_muni_field, valid_de_field, valid_a_field,
                           data_alta_field, data_baixa_field]
        self.work_polygon_layer.dataProvider().addAttributes(new_fields_list)
        self.work_polygon_layer.updateFields()

    def fill_fields(self):
        """ Fill the new fields with the necessary data """
        with edit(self.work_polygon_layer):
            for polygon in self.work_polygon_layer.getFeatures():
                polygon['CodiMuni'] = self.municipality_codi_ine
                polygon['AreaMunMMC'] = polygon['Sup_CDT']
                polygon['NomMuni'] = str(self.municipality_name)
                polygon['ValidDe'] = self.municipality_valid_de
                polygon['DataAlta'] = self.data_alta
                self.work_polygon_layer.updateFeature(polygon)

    def return_superficie_cdt(self):
        """
        Get the municipality area

        :return: superficie_cdt: Official area of the municipality
        :rtype: str
        """
        superficie_cdt = ''
        for polygon in self.work_polygon_layer.getFeatures():
            superficie_cdt = polygon['AreaMunMMC']

        return superficie_cdt

    def return_bounding_box(self):
        """
        Get the municipality bounding box

        :return: Bounding box of the municipality
        :rtype: str
        """
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

    def __init__(self,
                 municipality_id,
                 data_alta,
                 lines_layer,
                 dict_valid_de,
                 coast):
        """
        Constructor

        :param municipality_id: ID of the municipality
        :type municipality_id: str

        :param data_alta: Update date
        :type data_alta: str

        :param lines_layer: Lines layer of the municipality
        :type lines_layer: QgsVectorLayer

        :param: dict_valid_de: Dictionary with the ValidDe date of every line
        :type dict_valid_de: dict

        :param coast: Indicates if the municipality has coast or not
        :type coast: bool
        """
        GeneradorMMC.__init__(self, municipality_id, data_alta, coast)
        self.coast_line_id = None
        self.work_lines_layer = lines_layer
        # Es important indicar el crs al crear la capa, si no la geometria no es veu correctament
        self.temp_coast_line_layer = QgsVectorLayer('LineString?crs=epsg:25831', 'Coast_line', 'memory')
        self.temp_coast_line_table = QgsVectorLayer('LineString', 'Coast_line_table', 'memory')
        self.temp_coast_full_table = QgsVectorLayer('LineString', 'Coast_full_table', 'memory')
        self.dict_valid_de = dict_valid_de

    def generate_coast_line_layer(self):
        """
        Generate the municipality's coast line layer

        :return coast_line_layer: Layer of the municipality's coast line
        :rtype: QgsVectorLayer
        """
        self.add_fields('layer')
        if self.coast:
            self.export_coast_line_layer()
        self.export_layer()

        coast_line_layer = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_LiniaCosta.shp'))
        return coast_line_layer

    def generate_coast_line_table(self):
        """
        Generaate the municipality's coast line table

        :return coast_line_layer: DBF attributes table of the municipality's coast line's layer
        :rtype: QgsVectorLayer
        """
        self.add_fields('table')
        if self.coast:
            self.fill_fields_table()
        self.export_table('table')

        coast_line_table = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_LiniaCostaTaula.dbf'))
        return coast_line_table

    def generate_coast_full_bt5m_table(self):
        """
        Generate the municipality's coast line BT5 full

        :return coast_line_full: DBF list table of the municipality's coast line's layer
        :rtype: QgsVectorLayer
        """
        self.add_fields('full')
        if self.coast:
            self.fill_fields_full_table()
        self.export_table('full')

        coast_line_full = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_FullBT5MCosta.dbf'))
        return coast_line_full

    def add_fields(self, entity):
        """ Add the necessary fields to the selected layer """
        # Set new fields
        id_linia_field, valid_de_field, valid_a_field, data_alta_field, data_baixa_field = get_common_fields()
        name_municipality_1_field = QgsField(name='NomTerme1', type=QVariant.String, typeName='text', len=100)
        codi_muni_field = QgsField(name='CodiMuni', type=QVariant.String, typeName='text', len=6)
        # Full BT5M fields
        id_full_field = QgsField(name='IdFullBT5M', type=QVariant.String, typeName='text', len=6)
        versio_field = QgsField(name='Versio', type=QVariant.String, typeName='text', len=5)
        revisio_field = QgsField(name='Revisio', type=QVariant.String, typeName='text', len=2)
        correccio_field = QgsField(name='Correccio', type=QVariant.String, typeName='text', len=1)

        if entity == 'layer':
            new_fields_list = [id_linia_field, name_municipality_1_field, valid_de_field, valid_a_field, data_alta_field,
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
        """ Export the coast line layer """
        coast_line_geom = None
        for line in self.work_lines_layer.getFeatures():
            line_id = line['IdLinia']
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == int(line_id))]
            if line_data['LIMCOSTA'] == 'S':
                self.coast_line_id = line_id
                coast_line_geom = line.geometry()
                with edit(self.work_lines_layer):
                    self.work_lines_layer.deleteFeature(line.id())   # Delete the coast line from the lines layer

        with edit(self.temp_coast_line_layer):
            coast_line = QgsFeature()
            coast_line.setGeometry(coast_line_geom)
            coast_line.setAttributes([self.coast_line_id, str(self.municipality_name), self.dict_valid_de[int(self.coast_line_id)], '',
                                      self.data_alta, ''])
            self.temp_coast_line_layer.dataProvider().addFeatures([coast_line])

    def fill_fields_table(self):
        """ FIll the table's fields with the necessary data """
        with edit(self.temp_coast_line_table):
            for line in self.temp_coast_line_layer.getFeatures():
                line_id = line['IdLinia']
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromWkt('LineString()'))
                feature.setAttributes([line_id, self.municipality_codi_ine])
                self.temp_coast_line_table.dataProvider().addFeatures([feature])

    def fill_fields_full_table(self):
        """ Fill the BT5 full with the necessary data """
        with open(COAST_TXT, 'r') as f:
            fulls = f.readlines()
        with edit(self.temp_coast_full_table):
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

    def export_layer(self):
        """ Export the coast line layer """
        QgsVectorFileWriter.writeAsVectorFormat(self.temp_coast_line_layer,
                                                os.path.join(GENERADOR_WORK_DIR, 'MM_LiniaCosta.shp'),
                                                'utf-8', self.crs, 'ESRI Shapefile')

    def export_table(self, table_type):
        """
        Export the coast line table as a dbf file.

        PyQGIS is not able to manage and export a standalone DBF file, so the working way is exporting the table as shapefile
        and then deleting all the associated files except the DBF one.

        :param table_type: indicates whic table to export
        :type table_type: str
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
    def __init__(self, municipality_id):
        """
        Constructor

        :param municipality_id: ID of the municipality
        """
        GeneradorMMC.__init__(self, municipality_id)

    def get_municipality_normalized_name(self):
        """ Get the municipality's normalized name, without accent marks or special characters """
        muni_data = self.arr_nom_municipalities[np.where(self.arr_nom_municipalities['id_area'] == f'"{self.municipality_id}"')]
        muni_norm_name = muni_data['nom_muni_norm'][0]

        return muni_norm_name

    def get_municipality_codi_ine(self):
        """ Get the municipality INE ID """
        muni_data = self.arr_nom_municipalities[np.where(self.arr_nom_municipalities['id_area'] == f'"{self.municipality_id}"')]
        codi_ine = muni_data['codi_ine_muni'][0].strip('"\'')

        return codi_ine

    def check_mm_exists(self):
        """ Check if the input municipality exists as a Municipal Map into the database """
        mapa_muni_table = self.pg_adt.get_table('mapa_muni_icc')
        mapa_muni_table.selectByExpression(f'"codi_muni"=\'{self.municipality_codi_ine}\' and "vig_mm" is True',
                                           QgsVectorLayer.SetSelection)
        count = mapa_muni_table.selectedFeatureCount()
        if count == 0:
            return False
        else:
            return True

    def validate_inputs(self):
        """ Validate that all the inputs exists and are correct """
        municipality_input_dir_exists = self.check_municipality_input_dir()
        if not municipality_input_dir_exists:
            return False
        municipality_input_data_ok = self.check_municipality_input_data()
        if not municipality_input_data_ok:
            return False

        return True

    def check_municipality_input_dir(self):
        """ Check that exists the municipality's folder into the inputs directory """
        if not os.path.exists(self.municipality_input_dir):
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText(f"No existeix la carpeta del municipality al directori d'entrades. El nom que ha de tenir "
                          f"es '{self.municipality_normalized_name}'.")
            box.exec_()
            return False
        else:
            return True

    def check_municipality_input_data(self):
        """ Check that exists the Shapefiles' folder and all the shapefiles needed """
        if not os.path.exists(self.shapefiles_input_dir):
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText("No existeix la carpeta de Shapefiles a la carpeta del municipality")
            box.exec_()
            return False

        shapefiles_list = os.listdir(self.shapefiles_input_dir)
        layers_missing = []
        for layer in ('MM_Fites.shp', 'MM_Linies.shp', 'MM_Poligons.shp'):
            if layer not in shapefiles_list:
                layers_missing.append(layer)

        if len(layers_missing) == 0:
            return True
        else:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            if len(layers_missing) == 1:
                box.setText(f"No existeix la capa {layer} a la carpeta de Shapefiles del municipi")
            elif len(layers_missing) > 1:
                box.setText("No existeixen les següents capes a la carpeta de Shapefiles del municipi")
                for layer_missing in layers_missing:
                    box.setText(f"    - {layer_missing}")
            box.exec_()
            return False


class GeneradorMMCMetadataTable(GeneradorMMC):

    def __init__(self, municipality_id, data_alta):
        GeneradorMMC.__init__(self, municipality_id, data_alta)
        if self.municipality_metadata_table:
            os.remove(self.metadata_table_path)
        self.municipality_metadata_table = QgsVectorLayer('LineString', 'Metadata_table', 'memory')

    def generate_metadata_table(self):
        """ Main entry point for generating the metadata table """
        self.add_fields()
        self.fill_fields()
        self.export_table()

    def add_fields(self):
        """ Add the necessary fields to the metadata table """
        id_linia_field = QgsField(name='IdLinia', type=QVariant.String, typeName='text', len=4)
        name_municipality_1_field = QgsField(name='NomMuni1', type=QVariant.String, typeName='text', len=100)
        name_municipality_2_field = QgsField(name='NomMuni2', type=QVariant.String, typeName='text', len=100)
        tipus_ua_field = QgsField(name='TipusUA', type=QVariant.String, typeName='text', len=17)
        tipus_reg_field = QgsField(name='TipusReg', type=QVariant.String, typeName='text', len=17)
        limit_prov_field = QgsField(name='LimProv', type=QVariant.String, typeName='text', len=1)
        id_municipality_1_field = QgsField(name='IdMuni1', type=QVariant.String, typeName='text', len=4)
        id_municipality_2_field = QgsField(name='IdMuni2', type=QVariant.String, typeName='text', len=4)
        data_acta_h_field = QgsField(name='DataActaH', type=QVariant.String, typeName='text', len=8)
        id_acta_field = QgsField(name='IdActa', type=QVariant.String, typeName='text', len=10)
        data_rep_field = QgsField(name='DataRep', type=QVariant.String, typeName='text', len=8)
        tip_rep_field = QgsField(name='TipusRep', type=QVariant.String, typeName='text', len=17)
        abast_rep_field = QgsField(name='AbastRep', type=QVariant.String, typeName='text', len=17)
        org_rep_field = QgsField(name='OrgRep', type=QVariant.String, typeName='text', len=50)
        fi_rep_field = QgsField(name='FiRep', type=QVariant.String, typeName='text', len=17)
        data_dogc_field = QgsField(name='DataDOGC', type=QVariant.String, typeName='text', len=8)
        data_pub_dogc_field = QgsField(name='DataPubDOGC', type=QVariant.String, typeName='text', len=8)
        tipus_dogc_field = QgsField(name='TipusDOGC', type=QVariant.String, typeName='text', len=30)
        tit_dogc_field = QgsField(name='TITDOGC', type=QVariant.String, typeName='text', len=300)
        esm_dogc_field = QgsField(name='EsmDOGC', type=QVariant.String, typeName='text', len=10)
        vig_dogc_field = QgsField(name='VigPubDOGC', type=QVariant.String, typeName='text', len=10)
        data_rec_field = QgsField(name='DataActaRec', type=QVariant.String, typeName='text', len=8)
        tipus_rec_field = QgsField(name='TipusActaRec', type=QVariant.String, typeName='text', len=17)
        vig_rec_field = QgsField(name='VigActaRec', type=QVariant.String, typeName='text', len=10)
        vig_aterm_field = QgsField(name='VigActaAterm', type=QVariant.String, typeName='text', len=10)
        data_mtt_field = QgsField(name='DataMTT', type=QVariant.String, typeName='text', len=8)
        abast_mtt_field = QgsField(name='AbastMTT', type=QVariant.String, typeName='text', len=8)
        vig_mtt_field = QgsField(name='VigMTT', type=QVariant.String, typeName='text', len=8)
        data_cdt_field = QgsField(name='DataCDT', type=QVariant.String, typeName='text', len=8)

        new_fields_list = [id_linia_field, name_municipality_1_field, name_municipality_2_field, tipus_ua_field, tipus_reg_field,
                           limit_prov_field, id_municipality_1_field, id_municipality_2_field, data_acta_h_field, id_acta_field, data_rep_field,
                           tip_rep_field, abast_rep_field, org_rep_field, fi_rep_field, data_dogc_field, data_pub_dogc_field,
                           tipus_dogc_field, tit_dogc_field, esm_dogc_field, vig_dogc_field, data_rec_field,
                           tipus_rec_field, vig_rec_field, vig_aterm_field, data_mtt_field, abast_mtt_field, vig_mtt_field,
                           data_cdt_field]
        self.municipality_metadata_table.dataProvider().addAttributes(new_fields_list)
        self.municipality_metadata_table.updateFields()

    def fill_fields(self):
        """ Fill the new metadata fields with the necessary data """
        with edit(self.municipality_metadata_table):
            for line_id in self.municipality_lines:
                nom_muni1 = self.municipalities_names_lines[line_id][0]
                nom_muni2 = self.municipalities_names_lines[line_id][1]
                # Data from the line data dict related to the line itself
                line_data = self.get_line_data(line_id)
                tipus_ua = line_data['TIPUSUA'][0]
                lim_prov = line_data['LIMPROV'][0]
                tipus_reg = line_data['TIPUSREG'][0]
                codi_muni1 = str(line_data['CODIMUNI1'][0])
                codi_muni2 = str(line_data['CODIMUNI2'][0])
                # Data from the Doc Acta
                acta_h_date, acta_h_id = self.get_acta_h_data(line_id)
                # Data from the Replantejament
                rep_date, rep_tip, rep_abast, rep_org, rep_fi = self.get_rep_data(line_id)
                # Data from the DOGC
                dogc_date, dogc_pub_date, dogc_tit, dogc_tipus, dogc_esm, dogc_vig = self.get_dogc_data(line_id)
                # Data from the Reconeixement
                rec_data, rec_tipus, rec_vig, rec_vig_aterm = self.get_rec_data(line_id)
                # Data from the MTT
                mtt_data, mtt_abast, mtt_vig = self.get_mtt_data(line_id)
                # Add the feature
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromWkt('LineString()'))
                feature.setAttributes([str(line_id), str(nom_muni1), str(nom_muni2), str(tipus_ua), str(tipus_reg),
                                       str(lim_prov), codi_muni1, codi_muni2, acta_h_date, acta_h_id, rep_date, rep_tip,
                                       rep_abast, rep_org, rep_fi, dogc_date, dogc_pub_date, dogc_tipus, dogc_tit, dogc_esm,
                                       dogc_vig, rec_data, rec_tipus, rec_vig, rec_vig_aterm, mtt_data, mtt_abast, mtt_vig,
                                       self.municipality_valid_de])
                self.municipality_metadata_table.dataProvider().addFeatures([feature])

    def get_line_data(self, line_id):
        """ Get the data from a single municipal line """
        line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]

        return line_data

    def get_acta_h_data(self, line_id):
        """ Get the line's historic acta data """
        acta_h_date, acta_h_id = ('',) * 2
        doc_acta_table = self.pg_adt.get_table('doc_acta')
        line_id_txt = line_id_2_txt(line_id)
        doc_acta_table.selectByExpression(f'"id_doc_acta" LIKE \'%REC_{line_id_txt}_%\'',
                                          QgsVectorLayer.SetSelection)
        if doc_acta_table.selectedFeatureCount() == 1:
            for feature in doc_acta_table.getSelectedFeatures():
                acta_h_date = feature['data'].toString('yyyyMMdd')
                acta_h_id = feature['id_acta_vell']
        # If there are more than 1 acta, select by the newest date
        elif doc_acta_table.selectedFeatureCount() > 1:
            date_list = []
            for feature in doc_acta_table.getSelectedFeatures():
                date_list.append(feature['data'].toString('yyyyMMdd'))
            newest = max(date_list)
            for feature in doc_acta_table.getSelectedFeatures():
                if feature['data'] == newest:
                    acta_h_date = feature['data'].toString('yyyyMMdd')
                    acta_h_id = feature['id_acta_vell']
                    break

        return acta_h_date, acta_h_id

    def get_rep_data(self, line_id):
        """ Get the line's replantejament data """
        rep_date, rep_tip, rep_abast, rep_org, rep_fi = ('',) * 5
        rep_table = self.pg_adt.get_table('replantejament')
        rep_table.selectByExpression(f'"id_linia"=\'{line_id}\' and "fi_rep" is True',
                                     QgsVectorLayer.SetSelection)
        if rep_table.selectedFeatureCount() == 1:
            for feature in rep_table.getSelectedFeatures():
                rep_date = feature['data_doc'].toString('yyyyMMdd')
                if 'Anàlisi' in feature['OBS_REP']:
                    rep_tip = 'ANÀLISI TÈCNICA'
                elif 'Informe' in feature['OBS_REP']:
                    rep_tip = 'INFORME'
                else:
                    rep_tip = 'REPLANTEJAMENT'
                rep_abast = feature['abast_rep']
                rep_org = feature['org_rep']
                if feature['fi_rep'] is True:
                    rep_fi = '1'
                else:
                    rep_fi = '0'
        elif rep_table.selectedFeatureCount() > 1:
            date_list = []
            for feature in rep_table.getSelectedFeatures():
                date_list.append(feature['data_doc'].toString('yyyyMMdd'))
            newest = max(date_list)
            for feature in rep_table.getSelectedFeatures():
                if feature['data_doc'] == newest:
                    rep_date = newest
                    if 'Anàlisi' in feature['OBS_REP']:
                        rep_tip = 'ANÀLISI TÈCNICA'
                    elif 'Informe' in feature['OBS_REP']:
                        rep_tip = 'INFORME'
                    else:
                        rep_tip = 'REPLANTEJAMENT'
                    rep_abast = feature['abast_rep']
                    rep_org = feature['org_rep']
                    if feature['fi_rep'] is True:
                        rep_fi = '1'
                    else:
                        rep_fi = '0'
                    break

        return rep_date, rep_tip, rep_abast, rep_org, rep_fi

    def get_dogc_data(self, line_id):
        """ Get the line's DOGC data """
        dogc_date, dogc_pub_date, dogc_tit, dogc_tipus, dogc_esm, dogc_vig = ('',) * 6
        dogc_table = self.pg_adt.get_table('pa_pub_dogc')
        dogc_table.selectByExpression(f'"id_linia"=\'{line_id}\' and "vig_pub_dogc" is True',
                                      QgsVectorLayer.SetSelection)
        if dogc_table.selectedFeatureCount() == 1:
            for feature in dogc_table.getSelectedFeatures():
                dogc_date = feature['data_doc'].toString('yyyyMMdd')
                dogc_pub_date = feature['data_pub_dogc'].toString('yyyyMMdd')
                dogc_tit = feature['tit_pub_dogc']
                dogc_tipus = DICT_TIPUS_PUB[feature['tip_pub_dogc']]
                if feature['esm_pub_dogc'] is True:
                    dogc_esm = '1'
                else:
                    dogc_esm = '0'
                if feature['vig_pub_dogc'] is True:
                    dogc_vig = '1'
                else:
                    dogc_vig = '0'
        elif dogc_table.selectedFeatureCount() > 1:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText(f"La linia {line_id} té més d'un DOGC vigent. Si us plau, "
                        f"revisa la data a la taula de metadades.")
            box.exec_()
            # Si hi ha més d'un DOGC vigent, fer una llista amb les dates d'aquelles publicacions que no siguin
            # correccions d'errades o alteracions i agafar la data del DOGC més nou
            date_list = []
            for feature in dogc_table.getSelectedFeatures():
                if feature['tip_pub_dogc'] != 2 and 'alteració' not in feature['obs_pub_dogc']:
                    date_list.append(feature['data_pub_dogc'].toString('yyyyMMdd'))
            newest = max(date_list)
            for feature in dogc_table.getSelectedFeatures():
                if feature['data_pub_dogc'] == newest:
                    dogc_date = feature['data_doc'].toString('yyyyMMdd')
                    dogc_pub_date = newest
                    dogc_tit = feature['tit_pub_dogc']
                    dogc_tipus = DICT_TIPUS_PUB[feature['tip_pub_dogc']]
                    if feature['esm_pub_dogc'] is True:
                        dogc_esm = '1'
                    else:
                        dogc_esm = '0'
                    if feature['vig_pub_dogc'] is True:
                        dogc_vig = '1'
                    else:
                        dogc_vig = '0'
                    break

        return dogc_date, dogc_pub_date, dogc_tit, dogc_tipus, dogc_esm, dogc_vig

    def get_rec_data(self, line_id):
        """ Get the line's reconeixement data """
        rec_data, rec_tipus, rec_vig, rec_vig_aterm = ('',) * 4
        rec_table = self.pg_adt.get_table('reconeixement')
        rec_table.selectByExpression(f'"id_linia"=\'{line_id}\' and "vig_act_rec" is True',
                                     QgsVectorLayer.SetSelection)
        if rec_table.selectedFeatureCount() == 1:
            for feature in rec_table.getSelectedFeatures():
                rec_data = feature['data_act_rec'].toString('yyyyMMdd')
                if feature['act_aterm'] is True:
                    rec_tipus = 'ATERMENAMENT'
                elif feature['act_aterm'] is False:
                    rec_tipus = 'RECONEIXEMENT'
                else:
                    rec_tipus = 'DESCONEGUT'
                if feature['vig_act_rec'] is True:
                    rec_vig = '1'
                else:
                    rec_vig = '0'
                if feature['act_aterm'] is True:
                    rec_vig_aterm = '1'
                else:
                    rec_vig_aterm = '0'
        elif rec_table.selectedFeatureCount() > 1:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText(f"La linia {line_id} té més d'una Acta de reconeixement vigent. Si us plau, "
                        f"revisa la data a la taula de metadades.")
            box.exec_()
            date_list = []
            for feature in rec_table.getSelectedFeatures():
                date_list.append(feature['data_act_rec'].toString('yyyyMMdd'))
            newest = max(date_list)
            for feature in rec_table.getSelectedFeatures():
                if feature['data_act_rec'] == newest:
                    rec_data = newest
                    if feature['act_aterm'] is True:
                        rec_tipus = 'ATERMENAMENT'
                    elif feature['act_aterm'] is False:
                        rec_tipus = 'RECONEIXEMENT'
                    else:
                        rec_tipus = 'DESCONEGUT'
                    if feature['vig_act_rec'] is True:
                        rec_vig = '1'
                    else:
                        rec_vig = '0'
                    if feature['act_aterm'] is True:
                        rec_vig_aterm = '1'
                    else:
                        rec_vig_aterm = '0'
                    break

        return rec_data, rec_tipus, rec_vig, rec_vig_aterm

    def get_mtt_data(self, line_id):
        """ Get the line's MTT data """
        mtt_data, mtt_abast, mtt_vig = ('',) * 3
        mtt_table = self.pg_adt.get_table('memoria_treb_top')
        mtt_table.selectByExpression(f'"id_linia"=\'{line_id}\' and "vig_mtt" is True',
                                     QgsVectorLayer.SetSelection)
        if mtt_table.selectedFeatureCount() == 1:
            for feature in mtt_table.getSelectedFeatures():
                mtt_data = feature['data_doc'].toString('yyyyMMdd')
                mtt_abast = feature['abast_mtt']
                if feature['vig_mtt'] is True:
                    mtt_vig = '1'
                else:
                    mtt_vig = '0'
        elif mtt_table.selectedFeatureCount() > 1:
            date_list = []
            for feature in mtt_table.getSelectedFeatures():
                date_list.append(feature['data_doc'].toString('yyyyMMdd'))
            newest = max(date_list)
            for feature in mtt_table.getSelectedFeatures():
                if feature['data'] == newest:
                    mtt_data = newest
                    mtt_abast = feature['abast_mtt']
                    if feature['vig_mtt'] is True:
                        mtt_vig = '1'
                    else:
                        mtt_vig = '0'
                    break

        return mtt_data, mtt_abast, mtt_vig

    def export_table(self):
        """ Export the metadata table """
        # Export the shapefile
        QgsVectorFileWriter.writeAsVectorFormat(self.municipality_metadata_table,
                                                os.path.join(GENERADOR_TAULES_ESPEC, f'{self.metadata_table_name}.shp'),
                                                'utf-8', self.crs, 'ESRI Shapefile')
        #  Delete the useless files
        for rm_format in ('.shp', '.shx', '.prj', '.cpg'):
            os.remove(os.path.join(GENERADOR_TAULES_ESPEC, f'{self.metadata_table_name}{rm_format}'))


class GeneradorMMCMetadata(GeneradorMMC):

    def __init__(self, municipality_id, data_alta, coast=False):
        GeneradorMMC.__init__(self, municipality_id, data_alta, coast)
        self.work_metadatata_file = os.path.join(GENERADOR_WORK_DIR, 'MM_Metadades.xml')
        self.output_metadata_name = f'mapa-municipal-{self.municipality_normalized_name}-ca-{self.municipality_valid_de}.xml'
        self.output_metadata_path = os.path.join(self.output_subdirectory_path, self.output_metadata_name)
        self.conv_valid_de = self.convert_date(self.municipality_valid_de)
        self.conv_data_alta = self.convert_date(self.data_alta[:8])
        self.pairs = self.get_municipalities_names_pairs()
        self.rec_list = self.get_line_rec_list()
        self.x_min, self.x_max, self.y_min, self.y_max = self.get_bounding_box()
        self.rep_quality_date = self.get_rep_quality_date()
        self.dogc_quality_date = self.get_dogc_quality_date()
        self.rec_quality_date = self.get_rec_quality_date()
        self.mtt_quality_date = self.get_mtt_quality_date()
        self.dates_actes_h = self.get_dates_xml('DataActaH')
        self.dates_rep = self.get_dates_xml('DataRep')
        self.dates_dogc = self.get_dates_xml('DataPubDOG')
        self.dates_rec = self.get_dates_xml('DataActaRe')
        self.dates_mtt = self.get_dates_xml('DataMTT')
        self.dates_actes_h_xml = self.get_dates_xml('DataActaH', True)
        self.dates_rep_xml = self.get_dates_xml('DataRep', True)
        self.dates_dogc_xml = self.get_dates_xml('DataPubDOG', True)
        self.dates_rec_xml = self.get_dates_xml('DataActaRe', True)
        self.dates_mtt_xml = self.get_dates_xml('DataMTT', True)
        self.pub_titles, self.pub_dogc_text = self.get_resolucions_edictes_dogc()

    def generate_metadata_file(self):
        """ Main entry point for generating the metadata file """
        shutil.copyfile(GENERADOR_METADATA_TEMPLATE, self.work_metadatata_file)

        # Open as xml file to replace values inside xml blocks that already exists
        with open(self.work_metadatata_file, encoding='utf-8') as f:
            tree = ET.parse(f)
            root = tree.getroot()

            for elem in root.iter():
                try:
                    elem.text = elem.text.replace('id_xml', f'limits-municipals-v1r0-{self.municipality_codi_ine}-{self.municipality_valid_de}')
                    elem.text = elem.text.replace('info_dades_titol', f'Mapa Municipal {self.municipality_nomens}')
                    elem.text = elem.text.replace('creacio_data', self.conv_data_alta)
                    elem.text = elem.text.replace('info_dades_data', self.conv_valid_de)
                    elem.text = elem.text.replace('info_dades_clau_lloc', self.municipality_name)
                    elem.text = elem.text.replace('info_dades_descripcio', f'Terme municipal {self.municipality_nomens}')
                    elem.text = elem.text.replace('font', self.pairs)
                    elem.text = elem.text.replace('verEspSHP', v_esp_shp)
                    elem.text = elem.text.replace('cita_data', data_esp_shp)
                    elem.text = elem.text.replace('nomInstitut', nom_institut)
                    elem.text = elem.text.replace('nomDepartament', nom_departament)
                    elem.text = elem.text.replace('long_limit_W', str(self.x_min))
                    elem.text = elem.text.replace('long_limit_E', str(self.x_max))
                    elem.text = elem.text.replace('long_limit_N', str(self.y_max))
                    elem.text = elem.text.replace('long_limit_S', str(self.y_min))
                    elem.text = elem.text.replace('qualitat_data_1', f'{self.rep_quality_date}T00:00:00')
                    elem.text = elem.text.replace('qualitat_data_2', f'{self.dogc_quality_date}T00:00:00')
                    elem.text = elem.text.replace('qualitat_data_3', f'{self.rec_quality_date}T00:00:00')
                    elem.text = elem.text.replace('qualitat_data_4', f'{self.mtt_quality_date}T00:00:00')
                    elem.text = elem.text.replace('qualitat_data_5', self.conv_valid_de)
                    elem.text = elem.text.replace('f_dogc', self.pub_dogc_text)
                except AttributeError:
                    pass

        tree.write(self.output_metadata_path, encoding='utf-8')

        # Open as a simple txt file to add the dates inside xml block that doesn't exist into the file
        with open(self.output_metadata_path) as f:
            xml_str = f.read()
        xml_str = xml_str.replace('dates_acth', self.dates_actes_h_xml)
        xml_str = xml_str.replace('dates_rep', self.dates_rep_xml)
        xml_str = xml_str.replace('dates_dogc', self.dates_dogc_xml)
        xml_str = xml_str.replace('dates_rec', self.dates_rec_xml)
        xml_str = xml_str.replace('dates_mtt', self.dates_mtt_xml)

        with open(self.output_metadata_path, "w") as f:
            f.write(xml_str)

        os.remove(self.work_metadatata_file)
        self.write_metadata_report()

    @staticmethod
    def convert_date(date):
        """ Transform a date from the date format to a string format """
        date_converted = f'{date[0:4]}-{date[4:6]}-{date[6:8]}'

        return date_converted

    def get_municipalities_names_pairs(self):
        """ Get the pairs of the municipalities names that share every line that make the municipality """
        names_pairs = []
        for line in self.municipality_lines:
            municipalities = self.municipalities_names_lines[line]
            pair = f'{municipalities[0]}-{municipalities[1]}'
            names_pairs.append(pair)

        pairs = ', '.join(names_pairs) + '.'

        return pairs

    def get_bounding_box(self):
        """ Get the municipality's bounding box """
        polygon_layer = QgsVectorLayer(os.path.join(GENERADOR_WORK_DIR, 'MM_Poligons.shp'))
        generador_mmc_polygon = GeneradorMMCPolygon(self.municipality_id, self.data_alta, polygon_layer)
        x_min, x_max, y_min, y_max = generador_mmc_polygon.return_bounding_box()

        return x_min, x_max, y_min, y_max

    def get_line_rec_list(self):
        """ Get a list with all the reconeixements from the municipality's lines """
        rec_list = []
        rec_table = self.pg_adt.get_table('reconeixement')
        for feature in self.municipality_metadata_table.getFeatures():
            line_id = feature['IdLinia']
            rec_table.selectByExpression(f'"id_linia"=\'{line_id}\' and "vig_act_rec" is True',
                                         QgsVectorLayer.SetSelection)
            for rec in rec_table.getSelectedFeatures():
                if rec['tipus_doc_ref'] == 2:
                    rec_list.append(line_id)

        return rec_list

    def get_rep_quality_date(self):
        """ Get the newest replantejament date """
        date_list = []
        for feature in self.municipality_metadata_table.getFeatures():
            if feature['TipusRep'] == 'REPLANTEJAMENT':
                date_list.append(feature['DataRep'])

        min_date = min(date_list)
        min_date_conv = self.convert_date(min_date)
        return min_date_conv

    def get_dogc_quality_date(self):
        """ Get the newest DOGC date """
        date_list = []
        for feature in self.municipality_metadata_table.getFeatures():
            date_list.append(feature['DataPubDOG'])

        max_date = max(date_list)
        max_date_conv = self.convert_date(max_date)
        return max_date_conv

    def get_rec_quality_date(self):
        """ Get the newest reconeixement date """
        date_list = []
        for feature in self.municipality_metadata_table.getFeatures():
            date_list.append(feature['DataActaRe'])

        max_date = max(date_list)
        max_date_conv = self.convert_date(max_date)
        return max_date_conv

    def get_mtt_quality_date(self):
        """ Get the newest MTT date """
        date_list = []
        for feature in self.municipality_metadata_table.getFeatures():
            date_list.append(feature['DataMTT'])

        max_date = max(date_list)
        max_date_conv = self.convert_date(max_date)
        return max_date_conv

    def get_dates_xml(self, field_name, xml=False):
        """ Convert a list of dates into a single string with all the dates """
        date_list = []
        xml_block_list = []
        # Get a list with all the dates
        for feature in self.municipality_metadata_table.getFeatures():
            data = feature[field_name]
            data_conv = self.convert_date(data)
            date_list.append(data_conv)

        if not xml:
            return date_list
        else:
            # Get a list with the xml blocks that contain the dates
            for date_ in date_list:
                xml = xml_block.replace('replace_date_here', date_)
                xml_block_list.append(xml)
            # Create a unique string with the xml blocks
            dates_xml = ''.join(xml_block_list) + '.'

            return str(dates_xml)

    def get_resolucions_edictes_dogc(self):
        """ Extract the title from a DOGC """
        pub_list = []
        for feature in self.municipality_metadata_table.getFeatures():
            if feature['TipusDOGC'] == 'EDICTE':
                pub_title = feature['TipusDOGC'].split(',')[0]
                pub_title = pub_title.replace('EDICTE', 'Edicte')
                pub_list.append(pub_title)
            elif feature['TipusDOGC'] == 'RESOLUCIO':
                pub_title = feature['TITDOGC'].split(',')
                pub_title = pub_title[0].split(' ')[-1]
                pub_list.append(pub_title)

        pub_titles = ', '.join(pub_list)
        pub_dogc_text = f'Darreres resolucions i/o edictes publicats al DOGC: {pub_titles}.'

        return pub_titles, pub_dogc_text

    def write_metadata_report(self):
        """ Write the metadata info into the report log """
        # Write the report
        with open(self.report_path, 'a+') as f:
            f.write("\n")
            f.write("METADADES\n")
            f.write("----------\n")
            f.write(f"Titol:                        Mapa Municipal {self.municipality_nomens}\n")
            f.write(f"Nom XML:                      {self.output_metadata_name}\n")
            f.write(f"Id XML:                       limits-municipals-v1r0-{self.municipality_codi_ine}-{self.municipality_valid_de}\n")
            f.write(f"Data creacio:                 {self.conv_data_alta}\n")
            f.write(f"Data CDT:                     {self.conv_valid_de}\n")
            f.write(f"Llista municipis (parelles):  {self.pairs}\n")
            f.write(f"Dates actes historiques:      {self.dates_actes_h}\n")
            f.write(f"Dates replantejaments:        {self.dates_rep}\n")
            f.write(f"Dates publicacions al DOGC:   {self.dates_dogc}\n")
            f.write(f"Resolucions i edictes:        {self.pub_titles}\n")
            f.write(f"Dates rec o DOGC:             {self.dates_rec}\n")
            f.write(f"Dates memories:               {self.dates_mtt}\n")
            f.write(f"Data arxiu especificacions:   {data_esp_shp}\n")
            f.write("\n")
            f.write("--------------------------------------------------------------------\n")
            if len(self.rec_list) == 0:
                f.write(f"Conte linies sense Acta de Reconeixement. La data del Pas3 ({self.rec_quality_date}) ha de ser posterior o igual a la del Pas2 ({self.dogc_quality_date}).\n")

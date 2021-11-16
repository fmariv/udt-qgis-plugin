# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the ExtractRepPackage class is defined. The main
function of this class is to run the automation process that extracts the
geometries and data of a boundary line as an Esri shapefile, transforms that
data to CAD file format and gets the Replantejament PDF file.
***************************************************************************/
"""

import os, shutil

from qgis.core import (QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem,)

from ..config import *
from .adt_postgis_connection import PgADTConnection


class ExtractRepPackage:
    """ Replantejament package extraction class """

    def __init__(self, line_id):
        # Initialize instance attributes
        # Set environment variables
        self.crs = QgsCoordinateReferenceSystem("EPSG:25831")
        # Input dependant
        self.line_id = line_id
        self.package_output_dir = os.path.join(USER_WORK, self.line_id)
        self.shp_dir = os.path.join(self.package_output_dir, 'SHP')
        self.cad_dir = os.path.join(self.package_output_dir, 'CAD')
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        # DB entities
        self.lines_mem_layer = self.pg_adt.get_layer('v_tram_linia_rep', 'id_tram_linia')
        self.points_mem_layer = self.pg_adt.get_layer('v_fita_rep', 'id_fita')
        # Layers
        self.lines_layer, self.points_layer = None, None

    def extract_package(self):
        """   """
        self.make_package_dir()
        self.extract_data()
        self.convert_data()
        self.copy_pdf()

    def make_package_dir(self):
        """  """
        if not os.path.exists(self.package_output_dir):
            os.mkdir(self.package_output_dir)
            if not os.path.exists(self.shp_dir):
                os.mkdir(self.shp_dir)
            if not os.path.exists(self.cad_dir):
                os.mkdir(self.cad_dir)

    # #######################
    # Data extraction
    def extract_data(self):
        """  """
        self.extract_lines_data()
        self.extract_points_data()

    def extract_lines_data(self):
        """  """
        self.lines_mem_layer.selectByExpression(f'"id_linia"={int(self.line_id)}', QgsVectorLayer.SetSelection)
        lines_layer_path = os.path.join(self.shp_dir, f'{self.line_id}_LiniaTerme.shp')
        if not os.path.exists(lines_layer_path):
            QgsVectorFileWriter.writeAsVectorFormat(self.lines_mem_layer, lines_layer_path, 'utf-8', self.crs,
                                                    'ESRI Shapefile', onlySelected=True)
        self.lines_layer = QgsVectorLayer(lines_layer_path)

    def extract_points_data(self):
        """  """
        self.points_mem_layer.selectByExpression(f'"id_linia"={int(self.line_id)}', QgsVectorLayer.SetSelection)
        points_layer_path = os.path.join(self.shp_dir, f'{self.line_id}_Fites.shp')
        if not os.path.exists(points_layer_path):
            QgsVectorFileWriter.writeAsVectorFormat(self.points_mem_layer, points_layer_path, 'utf-8', self.crs,
                                                    'ESRI Shapefile', onlySelected=True)
        self.points_layer = QgsVectorLayer(points_layer_path)

    # #######################
    # Data conversion
    def convert_data(self):
        """  """
        self.convert_lines_to_cad()
        self.convert_points_to_cad()

    def convert_lines_to_cad(self):
        """  """
        lines_layer_path = os.path.join(self.cad_dir, f'{self.line_id}_LiniaTerme.dxf')
        if not os.path.exists(lines_layer_path):
            QgsVectorFileWriter.writeAsVectorFormat(self.lines_layer, lines_layer_path, "utf-8", self.crs, "DXF",
                                                    skipAttributeCreation=True)

    def convert_points_to_cad(self):
        """  """
        points_layer_path = os.path.join(self.cad_dir, f'{self.line_id}_Fites.dxf')
        if not os.path.exists(points_layer_path):
            QgsVectorFileWriter.writeAsVectorFormat(self.points_layer, points_layer_path, "utf-8", self.crs, "DXF",
                                                    skipAttributeCreation=True)

    # #######################
    # PDF file extraction
    def copy_pdf(self):
        """  """
        line_dir = os.path.join(LINES_DIR, self.line_id)
        ed50_rep_dir = os.path.join(line_dir, ED50_REP_DIR)
        etrs89_rep_dir = os.path.join(line_dir, ETRS89_REP_DIR)
        # First check in the ETRS89 directory
        etrs89_file_list = os.listdir(etrs89_rep_dir)
        if etrs89_file_list:
            # Check if only exists one PDF file. If not, search for the newest one
            if len(etrs89_file_list) == 1:
                rep_pdf_name = etrs89_file_list[0]
                rep_pdf_path = os.path.join(etrs89_rep_dir, rep_pdf_name)
            else:
                # Search for the newest document
                rep_pdf_name, rep_pdf_path = self.search_newest_doc(etrs89_file_list)
        else:
            # If the doc is not in ETRS89, search in the ED50 directory
            ed50_file_list = os.listdir(ed50_rep_dir)
            if len(ed50_file_list) == 1:
                rep_pdf_name = ed50_file_list[0]
                rep_pdf_path = os.path.join(ed50_rep_dir, rep_pdf_name)
                print(rep_pdf_path)
            else:
                # Search for the newest document
                rep_pdf_name, rep_pdf_path = self.search_newest_doc(ed50_rep_dir)

        # Copy the file to the new package directory
        new_rep_pdf_path = os.path.join(self.package_output_dir, rep_pdf_name)
        shutil.copyfile(rep_pdf_path, new_rep_pdf_path)

    def search_newest_doc(self, directory_path):
        """  """
        dates = [file_name[9:17] for file_name in directory_path]
        vigent_date = max(dates)
        for file_name in directory_path:
            if vigent_date in file_name:
                rep_pdf_path = os.path.join(directory_path, file_name)

        return file_name, rep_pdf_path

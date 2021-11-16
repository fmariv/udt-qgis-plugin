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

import os

from qgis.core import (QgsVectorLayer,
                       QgsField,
                       QgsVectorLayerJoinInfo,
                       QgsFeature,
                       QgsVectorFileWriter,
                       QgsCoordinateTransformContext,
                       QgsProject,
                       QgsCoordinateReferenceSystem,
                       QgsMessageLog,
                       Qgis)
from qgis.core.additions.edit import edit

from ..config import *
from .adt_postgis_connection import PgADTConnection


class ExtractRepPackage:
    """ Replantejament package extraction class """

    def __init__(self, line_id):
        # Initialize instance attributes
        # Set environment variables
        # Input dependant
        self.line_id = line_id
        self.package_output_dir = os.path.join(USER_WORK, self.line_id)
        self.shp_dir = os.path.join(self.package_output_dir, 'SHP')
        self.cad_dir = os.path.join(self.package_output_dir, 'CAD')
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        # DB entities
        self.lines_mem_layer = self.pg_adt.get_layer('v_tram_linia_mem', 'id_tram_linia')
        self.points_mem_layer = self.pg_adt.get_layer('v_fita_mem', 'id_fita')
        # Layers
        self.lines_temp_layer, self.points_temp_layer = None, None

    def extract_package(self):
        """   """
        self.make_package_dir()
        self.extract_data()
        self.convert_data()
        self.get_rep_pdf()

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
        pass

    def extract_points_data(self):
        """  """
        pass

    # #######################
    # Data conversion
    def convert_data(self):
        """  """
        self.convert_lines_to_cad()
        self.convert_points_to_cad()

    def convert_lines_to_cad(self):
        """  """
        pass

    def convert_points_to_cad(self):
        """  """
        pass

    # #######################
    # PDF file extraction
    def get_rep_pdf(self):
        """  """
        pass

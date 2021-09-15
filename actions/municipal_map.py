# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the MunicipalMap class is defined. The main function
of this class is to run the automation process that edits a Municipal map layout,
in order to automatically add some information related to the document and the municipi
and make the layout editable for the user.
***************************************************************************/
"""

import numpy as np
import re
from datetime import datetime
import os

from qgis.core import (QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem,
                       QgsField,
                       QgsFeature,
                       QgsGeometry,
                       QgsProject,
                       QgsMessageLog,
                       QgsWkbTypes,
                       QgsFillSymbol,
                       QgsLayoutExporter,
                       QgsProcessingFeedback)
from PyQt5.QtCore import QVariant
from qgis.core.additions.edit import edit

from ..config import *
from .adt_postgis_connection import PgADTConnection


class MunicipalMap:
    """ Municipal map generation class """

    def __init__(self, municipi_id, input_directory, layout_size, generate_shadow):
        # Initialize instance attributes
        # Set environment variables
        self.municipi_id = municipi_id
        self.input_directory = input_directory
        self.layout_size = layout_size
        self.generate_shadow = generate_shadow
        # Common
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        self.project = QgsProject.instance()
        self.arr_municipi_data = np.genfromtxt(LAYOUT_MUNI_DATA, dtype=None, encoding='utf-8-sig', delimiter=';', names=True)
        self.layout_manager = self.project.layoutManager()
        # Input dependant
        # Paths
        self.set_directories_paths()
        # Layers
        self.set_layers()
        # The layout size determines the layout to generate
        self.layout_name = self.get_layout_name()
        self.layout = self.layout_manager.layoutByName(self.layout_name)

    # #######################
    # Set up the environment
    def get_layout_name(self):
        """  """
        return SIZE[self.layout_size]

    def set_directories_paths(self):
        """  """
        self.shapes_dir = os.path.join(self.input_directory, 'ESRI/Shapefiles')
        self.dgn_dir = os.path.join(self.input_directory, 'ESRI/DGN')
        self.dxf_dir = os.path.join(self.input_directory, 'ESRI/DXF')

    def set_layers(self):
        """  """
        self.lines_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Linies.shp'))
        self.points_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Fites.shp'))
        self.polygon_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Poligons.shp'))
        self.neighbor_lines_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Lveines.shp'))
        self.neighbor_polygons_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Municipisveins.shp'))
        self.place_name_layer = QgsVectorLayer(os.path.join(self.shapes_dir, 'MM_Nuclis.shp'))

    # #######################
    # Generate the Municipal map layout
    def generate_municipal_map(self):
        """  """
        pass

    # #######################
    # Generate the shadow
    def generate_shadow(self):
        """  """
        pass

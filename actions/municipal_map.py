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

    def __init__(self, municipi_id, input_directory, layout_size, generate_hillshade):
        # Initialize instance attributes
        # Set environment variables
        self.municipi_id = municipi_id
        self.input_directory = input_directory
        self.layout_size = layout_size
        self.generate_hillshade = generate_hillshade
        # Common
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        self.project = QgsProject.instance()
        self.arr_municipi_data = np.genfromtxt(LAYOUT_MUNI_DATA, dtype=None, encoding='utf-8-sig', delimiter=';', names=True)

        self.layout_manager = self.project.layoutManager()
        # Input dependant
        self.municipi_name = self.get_municipi_name()
        # Paths
        self.set_directories_paths()
        # Layers
        self.set_layers()
        # Layer dependant
        self.municipi_sup = self.get_municipi_sup()
        # The layout size determines the layout to generate
        self.layout_name = self.get_layout_name()
        self.layout = self.layout_manager.layoutByName(self.layout_name)

    # #######################
    # Setters & Getters
    def get_layout_name(self):
        """  """
        return SIZE[self.layout_size]

    def get_municipi_name(self):
        """  """
        data = np.where(self.arr_municipi_data['id_area'] == str(self.municipi_id))
        index = data[0]
        muni_data = data[index][0]
        muni_name = muni_data[1]

        return muni_name

    def get_municipi_sup(self):
        """  """
        sup = None
        for polygon in self.polygon_layer.getFeatures():
            sup = polygon['Sup_CDT']
            break

        return sup

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

        self.map_layers = (self.lines_layer, self.points_layer, self.polygon_layer, self.neighbor_lines_layer,
                           self.neighbor_polygons_layer, self.place_name_layer)

    # #######################
    # Generate the Municipal map layout
    def generate_municipal_map(self):
        """  """
        pass

    def zoom_to_active_layer(self, iface):
        """"  """
        self.add_map_layers()
        iface.zoomToActiveLayer()

    def add_map_layers(self):
        """  """
        for layer in self.map_layers:
            self.project.addMapLayer(layer)

    def add_layers_styles(self):
        """  """
        layers = self.project.mapLayers().values()
        for layer in layers:
            if layer.name() == 'MM_Poligons':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'poligon.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Fites':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'fites.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Lveines':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'linies_veines.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Linies':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'linies.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'MM_Municipisveins':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'etiquetes_municipi_veins.qml'))
                layer.triggerRepaint()
            elif layer.name() == 'Nuclis':
                layer.loadNamedStyle(os.path.join(LAYOUT_MAPA_MUNICIPAL_STYLE_DIR, 'nuclis.qml'))
                layer.triggerRepaint()

    def add_hillshade_style(self):
        """  """
        pass

    # #######################
    # Generate the shadow
    def generate_shadow(self):
        """  """
        pass

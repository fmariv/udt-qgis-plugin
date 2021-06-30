# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the decimetritzador class is defined. The main function
of this class is to take both points and lines layers and transform them
decimals in order to round them to 1.
***************************************************************************/
"""

import os

from ..utils import *

from qgis.core.additions.edit import edit
from qgis.core import QgsVectorLayer, QgsDataSourceUri, QgsProviderRegistry, QgsPoint, QgsGeometry
from PyQt5.QtWidgets import QMessageBox


class Decimetritzador:
    def __init__(self, doc_delim_directory):
        # Layers and paths
        self.doc_delim = doc_delim_directory
        self.point_layer, self.line_layer = None, None
        # Message box
        self.box_error = QMessageBox()
        self.box_error.setIcon(QMessageBox.Critical)

    def decimetritzar(self):
        """  """
        self.set_layers()
        self.decimetritzar_points()
        self.decimetritzar_lines()

    def set_layers(self):
        """  """
        self.point_layer = QgsVectorLayer(os.path.join(self.doc_delim, 'Cartografia', 'Punt.shp'))
        self.line_layer = QgsVectorLayer(os.path.join(self.doc_delim, 'Cartografia', 'Lin_TramPpta.shp'))

    def decimetritzar_points(self):
        """  """
        with edit(self.point_layer):
            for point in self.point_layer.getFeatures():
                geom = point.geometry()
                coord_x = geom.get().x()
                coord_y = geom.get().y()
                z = geom.get().z()
                # Round coordinates
                x, y = round_coordinates(coord_x, coord_y)
                # Create new geometry
                rounded_point = QgsPoint(x, y, z)
                rounded_geom = QgsGeometry(rounded_point)
                # Set new geometry
                self.point_layer.changeGeometry(point.id(), rounded_geom)

    def decimetritzar_lines(self):
        """  """
        pass

    def check_input_data(self):
        """  """
        cartography_directory = os.path.join(self.doc_delim, 'Cartografia')
        if os.path.isdir(cartography_directory):
            points_layer = os.path.join(cartography_directory, 'Punt.shp')
            lines_layer = os.path.join(cartography_directory, 'Lin_TramPpta.shp')
            if os.path.exists(points_layer) and os.path.exists(lines_layer):
                return True
            else:
                self.box_error.setText("Falta la capa de Punts o Trams a la carpeta de Cartografia")
                self.box_error.exec_()
                return False
        else:
            self.box_error.setText("La carpeta DocDelim no té carpeta de Cartografia")
            self.box_error.exec_()
            return False


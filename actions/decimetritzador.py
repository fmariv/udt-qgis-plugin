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

from qgis.core import QgsVectorLayer, QgsDataSourceUri, QgsProviderRegistry
from PyQt5.QtWidgets import QMessageBox


class Decimetritzador:
    def __init__(self, doc_delim_directory):
        self.doc_delim = doc_delim_directory
        self.box_error = QMessageBox()
        self.box_error.setIcon(QMessageBox.Critical)

    def decimetritzar(self):
        """  """
        self.decimetritzar_points()
        self.decimetritzar_lines()

    def decimetritzar_points(self):
        """  """
        pass

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


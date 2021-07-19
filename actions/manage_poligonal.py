# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the ManagePoligonal class is defined. The main function
of this class is to run the automation process that updates the poligonal table
with the poligonal's point layer reprojected ETRS89 coordinates.
***************************************************************************/
"""

import datetime
import os

from qgis.core import (QgsVectorLayer,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem,
                       QgsField,
                       QgsFeature,
                       QgsGeometry,
                       QgsProject)
from qgis.core.additions.edit import edit
from PyQt5.QtWidgets import QMessageBox

from ..config import *
from .adt_postgis_connection import PgADTConnection


class ManagePoligonal:

    def __init__(self, doc_delim_directory):
        # Layers and paths
        self.doc_delim = doc_delim_directory
        self.polig_points_layer, self.polig_table = None, None
        # Message box
        self.box_error = QMessageBox()
        self.box_error.setIcon(QMessageBox.Critical)

    def update_poligonal_table(self):
        """   """
        pass

    def check_input_data(self):
        """ Check that exists all the necessary input data into the input directory """
        cartography_directory = os.path.join(self.doc_delim, 'Cartografia')
        tables_directory = os.path.join(self.doc_delim, 'Taules')

        # Check polig points layer
        if os.path.isdir(cartography_directory):
            polig_points_layer = os.path.join(cartography_directory, 'Pto_Polig.shp')
            if not os.path.exists(polig_points_layer):
                self.box_error.setText("Falta la capa de Punts de poligonal a la carpeta de Cartografia")
                self.box_error.exec_()
                return False
        else:
            self.box_error.setText("El directori introduït no té carpeta de Cartografia")
            self.box_error.exec_()
            return False

        # Check polig table
        if os.path.isdir(tables_directory):
            polig_table = os.path.join(tables_directory, 'POLIGONA.dbf')
            if not os.path.exists(polig_table):
                self.box_error.setText("Falta la taula POLIGONA a la carpeta de Taules")
                self.box_error.exec_()
                return False
        else:
            self.box_error.setText("El directori introduït no té carpeta de Taules")
            self.box_error.exec_()
            return False

        return True

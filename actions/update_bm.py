# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the UpdateBM class is defined. The main function
of this class is to run the automation process that updates the Municipal Base
of Catalonia with the newest boundary lines.
***************************************************************************/
"""

from datetime import datetime
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


class UpdateBM:
    """ Update BM-5M class """

    def __init__(self, date_last_update):
        # Initialize instance attributes
        # Common
        self.date_last_update = date_last_update
        self.current_date = datetime.now().strftime("%Y%m%d%M%S")
        # Set input layers
        self.lines_input_path = os.path.join(UPDATE_BM_INPUT_DIR, 'bm5mv21sh0tlm1_ACTUAL_0.shp')
        self.lines_input_layer = QgsVectorLayer(os.path.join(self.lines_input_path))

    # #####################
    def update_bm(self):
        """  """
        pass

    # #####################
    # Check the data that the proccess needs
    def check_bm_data(self):
        """  """
        input_layers = self.check_input_lines_layer()
        if not input_layers:
            return
        self.check_date_last_update_inputs()

    def check_input_lines_layer(self):
        """  """
        if os.path.exists(self.lines_input_path):
            return True
        else:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText("Falta la capa de línies de la BM\nanterior a la carpeta d'entrades.")
            box.exec_()
            return False

    def check_date_last_update_inputs(self):
        """  """
        self.lines_input_layer.selectByExpression(f'"DATAALTA"=\'{self.date_last_update}\'')
        count = self.lines_input_layer.selectedFeatureCount()
        if count == 0:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText("La data de l'última actualització introduïda\nno existeix a les dades d'entrada.")
            box.exec_()
            return False
        else:
            return True

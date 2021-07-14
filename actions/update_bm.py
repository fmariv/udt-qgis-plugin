# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the UpdateBM class is defined. The main function
of this class is to run the automation process that updates the Municipal Base
of Catalonia with the newest boundary lines.
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

# 202001011200

class UpdateBM:
    """ Update BM-5M class """

    def __init__(self, date_last_update):
        # Initialize instance attributes
        # Common
        self.date_last_update = date_last_update
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        # Get current datetime and add 1 hour
        self.new_data_alta = self.get_new_data_alta()
        self.date_last_update_tr = self.convert_str_to_date()
        # Set input layers
        self.lines_input_path = os.path.join(UPDATE_BM_INPUT_DIR, 'bm5mv21sh0tlm1_ACTUAL_0.shp')
        self.lines_input_layer = QgsVectorLayer(os.path.join(self.lines_input_path))
        # Log config
        self.new_rep_list = []
        self.new_mtt_list = []

    # #####################
    def update_bm(self):
        """  """
        self.get_new_rep()
        self.get_new_mtt()

    def get_new_rep(self):
        """  """
        rep_table = self.pg_adt.get_table('replantejament')
        rep_table.selectByExpression(f'"data_doc" > \'{self.date_last_update_tr}\' and "data_doc" != \'9999-12-31\'')

        for rep in rep_table.getSelectedFeatures():
            line_id = rep['id_linia']
            self.new_rep_list.append(int(line_id))

    def get_new_mtt(self):
        """  """
        mtt_table = self.pg_adt.get_table('memoria_treb_top')
        mtt_table.selectByExpression(f'"data_doc" > \'{self.date_last_update_tr}\' and "data_doc" != \'9999-12-31\'')

        for mtt in mtt_table.getSelectedFeatures():
            line_id = mtt['id_linia']
            self.new_mtt_list.append(int(line_id))

    # ####################
    # Date and time management
    @staticmethod
    def get_new_data_alta():
        """  """
        current_date = datetime.datetime.now()
        hour = datetime.timedelta(hours=1)
        new_data_alta = current_date + hour

        return new_data_alta.strftime("%Y%m%d%H00")

    def convert_str_to_date(self):
        """   """
        date = f'{self.date_last_update[0:4]}-{self.date_last_update[4:6]}-{self.date_last_update[6:8]}'
        date_tr = datetime.datetime.strptime(date, '%Y-%m-%d')
        date_tr = date_tr.replace(second=0, microsecond=0)

        return date_tr

    # #####################
    # Check the data that the proccess needs
    def check_bm_data(self):
        """  """
        input_layers = self.check_input_lines_layer()
        if not input_layers:
            return
        date_last_update_ok = self.check_date_last_update_inputs()
        if not date_last_update_ok:
            return

        return True

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

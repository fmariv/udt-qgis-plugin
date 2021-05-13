# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the LineMMC class is defined. The main function
of this class is to run the automation process that exports the geometries
and generates the metadata of a municipal line.
***************************************************************************/
"""

from ..config import *
from .adt_postgis_connection import PgADTConnection

from qgis.core import QgsVectorLayer


class LineMMC(object):
    """ Line MMC Generation class """

    def __init__(self, line_id):
        self.line_id = int(line_id)
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()

    def check_line_exists(self):
        """  """
        line_exists_points_layer = self.check_line_exists_points_layer()
        line_exists_lines_layer = self.check_line_exists_lines_layer()

        return line_exists_points_layer, line_exists_lines_layer

    def check_line_exists_points_layer(self):
        """  """
        fita_mem_layer = self.pg_adt.get_layer('v_fita_mem', 'id_fita')
        fita_mem_layer.selectByExpression(f'"id_linia"=\'{self.line_id}\'', QgsVectorLayer.SetSelection)
        selected_count = fita_mem_layer.selectedFeatureCount()
        if selected_count > 0:
            return True
        else:
            return False

    def check_line_exists_lines_layer(self):
        """  """
        line_mem_layer = self.pg_adt.get_layer('v_tram_linia_mem', 'id_tram_linia')
        line_mem_layer.selectByExpression(f'"id_linia"=\'{self.line_id}\'', QgsVectorLayer.SetSelection)
        selected_count = line_mem_layer.selectedFeatureCount()
        if selected_count > 0:
            return True
        else:
            return False

    def generate_line_data(self):
        """  """
        pass

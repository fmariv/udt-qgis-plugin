# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the CheckMM class is defined. The main function
of this class is to check whether exist any municipi ready to make its Municipal
Map, which occurs when all of its boundary lines become official.
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

from PyQt5.QtWidgets import QMessageBox

from ..config import *
from .adt_postgis_connection import PgADTConnection


class CheckMM:
    """ Municipal Map checker class """

    def __init__(self):
        # Initialize instance attributes
        # Common
        self.current_date = datetime.now().strftime("%Y%m%d")
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        # Log
        self.report_path = os.path.join(CHECK_MM_LOCAL_DIR, f'Nous_MM_{self.current_date}.txt')
        # Entities
        self.area_muni_cat_table = self.pg_adt.get_table('area_muni_cat')
        self.dic_municipi = self.pg_adt.get_table('dic_municipi')
        self.mm_table = self.pg_adt.get_table('mapa_muni_icc')
        self.mtt_table = self.pg_adt.get_table('memoria_treb_top')

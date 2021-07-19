# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the UpdatePoligonal class is defined. The main function
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


class UpdatePoligonal:

    def __init__(self):
        pass

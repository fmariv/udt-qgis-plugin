# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the AgregadorMMC class is defined. The main function
of this class is to run the automation process that adds the newest municipal
maps to the previous layer of the Municipal Map of Catalonia.
***************************************************************************/
"""

import numpy as np
import os
import shutil
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QVariant
from qgis.core import (QgsVectorLayer,
                       QgsDataSourceUri,
                       QgsMessageLog,
                       QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransformContext,
                       QgsField,
                       QgsCoordinateTransform,
                       QgsFeature,
                       QgsGeometry,
                       QgsProject)
from PyQt5.QtWidgets import QMessageBox

from ..config import *
from ..utils import *
from .adt_postgis_connection import PgADTConnection


class AgregadorMMC(object):
    """ MMC Agregation class """

    def __init__(self, input_directory=None):
        pass

    # from qgis.core.additions.edit import edit
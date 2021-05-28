# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the EliminadorMMC class is defined. The main function
of this class is to run the automation process that removes a municipal
map and all of its features from the latest layer of the Municipal Map of Catalonia.
***************************************************************************/
"""

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


class EliminadorMMC:
    """ MMC Deletion class """

    def __init__(self):
        pass

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
from qgis.core.additions.edit import edit
from PyQt5.QtWidgets import QMessageBox

from ..config import *
from ..utils import *
from .adt_postgis_connection import PgADTConnection


class AgregadorMMC(object):
    """ MMC Agregation class """

    def __init__(self, input_directory=None):
        pass


def import_mmc_data(directory_path):
    """ Import the necessary data from the input directory to the working directory """
    crs = QgsCoordinateReferenceSystem("EPSG:25831")
    input_points_layer, input_lines_layer, input_polygons_layer, input_coast_lines_layer = (None,) * 4
    input_full_bt5_table, input_point_table, input_line_table = ('',) * 3
    # Paths
    for root, dirs, files in os.walk(directory_path):
        for file_ in files:
            if file_.endswith('_fita.shp'):
                input_points_layer = QgsVectorLayer(os.path.join(directory_path, file_))
            elif file_.endswith('_lter.shp'):
                input_lines_layer = QgsVectorLayer(os.path.join(directory_path, file_))
            elif file_.endswith('_munimmc.shp'):
                input_polygons_layer = QgsVectorLayer(os.path.join(directory_path, file_))
            elif file_.endswith('_lcos.shp'):
                input_coast_lines_layer = QgsVectorLayer(os.path.join(directory_path, file_))
            elif file_.endswith('_fbt5m.dbf'):
                input_full_bt5_table = os.path.join(directory_path, file_)
            elif file_.endswith('_fitammc.dbf'):
                input_point_table = os.path.join(directory_path, file_)
            elif file_.endswith('ltermmc.dbf'):
                input_line_table = os.path.join(directory_path, file_)

    # Copy dbf
    shutil.copyfile(input_full_bt5_table, os.path.join(AGREGADOR_WORK_DIR, 'bt5m_temp.dbf'))
    shutil.copyfile(input_point_table, os.path.join(AGREGADOR_WORK_DIR, 'fitesmmc_temp.dbf'))
    shutil.copyfile(input_line_table, os.path.join(AGREGADOR_WORK_DIR, 'liniesmmc_temp.dbf'))
    # Export layers
    QgsVectorFileWriter.writeAsVectorFormat(input_points_layer, os.path.join(AGREGADOR_WORK_DIR, 'fites_tmp.shp'),
                                            'utf-8', crs, 'ESRI Shapefile')
    QgsVectorFileWriter.writeAsVectorFormat(input_lines_layer, os.path.join(AGREGADOR_WORK_DIR, 'linies_tmp.shp'),
                                            'utf-8', crs, 'ESRI Shapefile')
    QgsVectorFileWriter.writeAsVectorFormat(input_polygons_layer, os.path.join(AGREGADOR_WORK_DIR, 'poligons_tmp.shp'),
                                            'utf-8', crs, 'ESRI Shapefile')
    QgsVectorFileWriter.writeAsVectorFormat(input_coast_lines_layer, os.path.join(AGREGADOR_WORK_DIR, 'linies_costa_tmp.shp'),
                                            'utf-8', crs, 'ESRI Shapefile')

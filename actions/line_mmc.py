# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the LineMMC class is defined. The main function
of this class is to run the automation process that exports the geometries
and generates the metadata of a municipal line.
***************************************************************************/
"""

import os

from PyQt5.QtCore import QVariant
from qgis.core import QgsVectorLayer, QgsCoordinateReferenceSystem, QgsVectorFileWriter, QgsMessageLog, QgsField

from ..config import *
from .adt_postgis_connection import PgADTConnection
from ..utils import *



class LineMMC(object):
    """ Line MMC Generation class """

    def __init__(self, line_id):
        self.line_id = line_id
        self.crs = QgsCoordinateReferenceSystem("EPSG:25831")
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        # Layers
        self.work_points_layer, self.work_lines_layer = None, None

    def check_line_exists(self):
        """  """
        line_exists_points_layer = self.check_line_exists_points_layer()
        line_exists_lines_layer = self.check_line_exists_lines_layer()

        return line_exists_points_layer, line_exists_lines_layer

    def check_line_exists_points_layer(self):
        """  """
        fita_mem_layer = self.pg_adt.get_layer('v_fita_mem', 'id_fita')
        fita_mem_layer.selectByExpression(f'"id_linia"=\'{int(self.line_id)}\'', QgsVectorLayer.SetSelection)
        selected_count = fita_mem_layer.selectedFeatureCount()
        if selected_count > 0:
            return True
        else:
            return False

    def check_line_exists_lines_layer(self):
        """  """
        line_mem_layer = self.pg_adt.get_layer('v_tram_linia_mem', 'id_tram_linia')
        line_mem_layer.selectByExpression(f'"id_linia"=\'{int(self.line_id)}\'', QgsVectorLayer.SetSelection)
        selected_count = line_mem_layer.selectedFeatureCount()
        if selected_count > 0:
            return True
        else:
            return False

    def generate_line_data(self):
        """  """
        # ########################
        # SET DATA
        # Copy data to work directory
        self.copy_data_to_work()
        # Set the layers paths
        self.work_points_layer, self.work_lines_layer = self.set_layers_paths()

        # ########################
        # GENERATION PROCESS
        line_mmc_points = LineMMCPoints(self.line_id, self.work_points_layer)
        line_mmc_points.generate_points_layer()

        ##########################
        # DATA EXPORTING
        # Make the output directories if they don't exist

    def copy_data_to_work(self):
        """  """
        # Points layer
        fita_mem_layer = self.pg_adt.get_layer('v_fita_mem', 'id_fita')
        fita_mem_layer.selectByExpression(f'"id_linia"=\'{self.line_id}\'', QgsVectorLayer.SetSelection)
        # Lines layer
        line_mem_layer = self.pg_adt.get_layer('v_tram_linia_mem', 'id_tram_linia')
        line_mem_layer.selectByExpression(f'"id_linia"=\'{self.line_id}\'', QgsVectorLayer.SetSelection)

        # Export layers to the work space
        QgsVectorFileWriter.writeAsVectorFormat(fita_mem_layer, os.path.join(LINIA_WORK_DIR, f'fites_{self.line_id}.shp'),
                                                'utf-8', self.crs, 'ESRI Shapefile', True)
        QgsVectorFileWriter.writeAsVectorFormat(line_mem_layer, os.path.join(LINIA_WORK_DIR, f'tram_linia_{self.line_id}.shp'),
                                                'utf-8', self.crs, 'ESRI Shapefile', True)
        # TODO: sin proyección

    def set_layers_paths(self):
        """  """
        work_points_layer = QgsVectorLayer(os.path.join(LINIA_WORK_DIR, f'fites_{self.line_id}.shp'))
        work_lines_layer = QgsVectorLayer(os.path.join(LINIA_WORK_DIR, f'tram_linia_{self.line_id}.shp'))

        return work_points_layer, work_lines_layer


class LineMMCPoints(LineMMC):

    def __init__(self, line_id, points_layer):
        LineMMC.__init__(self, line_id)
        self.work_points_layer = points_layer

    def generate_points_layer(self):
        """  """
        self.add_fields()
        self.fill_fields()
        self.delete_fields()

    def add_fields(self):
        """  """
        # Set new fields
        id_u_fita_field = QgsField(name='IdUfita', type=QVariant.String, typeName='text', len=10)
        id_fita_field = QgsField(name='IdFita', type=QVariant.String, typeName='text', len=18)
        id_sector_field = QgsField(name='IdSector', type=QVariant.String, typeName='text', len=1)
        id_fita_r_field = QgsField(name='IdFitaR', type=QVariant.String, typeName='text', len=3)
        num_termes_field = QgsField(name='NumTermes', type=QVariant.String, typeName='text', len=3)
        monument_field = QgsField(name='Monument', type=QVariant.String, typeName='text', len=1)
        id_linia_field, valid_de_field, valid_a_field, data_alta_field, data_baixa_field = get_common_fields()
        new_fields_list = [id_u_fita_field, id_fita_field, id_sector_field, id_fita_r_field, num_termes_field,
                           monument_field, id_linia_field]
        self.work_points_layer.dataProvider().addAttributes(new_fields_list)
        self.work_points_layer.updateFields()

    def fill_fields(self):
        """  """
        self.work_points_layer.startEditing()
        for point in self.work_points_layer.getFeatures():
            point_id_fita = coordinates_to_id_fita(point['point_x'], point['point_y'])
            point_r_fita = point_num_to_text(point['num_fita'])

            point['IdUFita'] = point['id_u_fita'][:-2]
            point['IdFita'] = point_id_fita
            point['IdFitaR'] = point_r_fita
            point['IdSector'] = point['num_sector']
            point['NumTermes'] = point['num_termes']
            point['IdLinia'] = int(point['id_linia'])
            # TODO tiene Valid de o Data alta? Preguntar Cesc
            if point['trobada'] == 1:
                point['Monument'] = 'S'
            else:
                point['Monument'] = 'N'

            self.work_points_layer.updateFeature(point)

        self.work_points_layer.commitChanges()

    def delete_fields(self):
        """  """
        delete_fields_list = list([*range(0, 31)])
        self.work_points_layer.dataProvider().deleteAttributes(delete_fields_list)
        self.work_points_layer.updateFields()

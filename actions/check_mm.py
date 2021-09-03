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
                       QgsProject,
                       QgsVectorLayerJoinInfo)

from ..config import *
from .adt_postgis_connection import PgADTConnection


class CheckMM:
    """ Municipal Map checker class """

    def __init__(self):
        # Initialize instance attributes
        # Common
        self.current_date = datetime.now().strftime("%Y%m%d")
        self.municipi_dict = {}
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        # Log
        self.report_path = os.path.join(CHECK_MM_LOCAL_DIR, f'Nous_MM_{self.current_date}.txt')
        # Entities
        self.area_muni_cat_table = self.pg_adt.get_table('area_muni_cat')
        self.line_table = self.pg_adt.get_table('linia')
        self.dic_municipi_table = self.pg_adt.get_table('dic_municipi')
        self.mapa_muni_table = self.pg_adt.get_table('mapa_muni_icc')
        self.mtt_table = self.pg_adt.get_table('memoria_treb_top')

    def get_new_mm(self):
        """  """
        for municipi in self.area_muni_cat_table.getFeatures():
            municipi_ine = municipi['codi_muni']
            # Check if the municipi has a considered MM
            municipi_mm_exists = self.check_municipi_mm(municipi_ine)
            if not municipi_mm_exists:
                municipi_id = municipi['id_area']
                # Get municipi boundary lines list
                municipi_line_list = self.get_municipi_lines(municipi_id)
                municipi_mm_ready = self.check_lines_mtt(municipi_line_list)
                if municipi_mm_ready:
                    municipi_name = self.get_municipi_name(municipi_ine)
                    self.municipi_dict[municipi_ine] = municipi_name

        self.write_mm_report()

    def check_municipi_mm(self, municipi_ine):
        """  """
        self.mapa_muni_table.selectByExpression(f'"codi_muni"=\'{municipi_ine}\' and "vig_mm" is True', QgsVectorLayer.SetSelection)
        count = self.mapa_muni_table.selectedFeatureCount()
        self.mapa_muni_table.removeSelection()
        if count == 1:
            return True
        else:
            return False

    def get_municipi_lines(self, municipi_id):
        """  """
        self.line_table.selectByExpression(f'"id_area_1"={municipi_id} or "id_area_2"={municipi_id}',
                                                QgsVectorLayer.SetSelection)
        municipi_line_list = []
        for line in self.line_table.getSelectedFeatures():
            line_id = line['id_linia']
            municipi_line_list.append(int(line_id))

        self.line_table.removeSelection()
        return municipi_line_list

    def check_lines_mtt(self, municipi_lines_list):
        """  """
        municipi_mm = True
        for line_id in municipi_lines_list:
            self.mtt_table.selectByExpression(f'"id_linia"={line_id} and "vig_mtt" is True', QgsVectorLayer.SetSelection)
            count = self.mtt_table.selectedFeatureCount()
            self.mtt_table.removeSelection()
            if count == 0:
                municipi_mm = False

        return municipi_mm

    def get_municipi_name(self, municipi_ine):
        """  """
        self.dic_municipi_table.selectByExpression(f'"codi_muni"=\'{municipi_ine}\'',
                                                    QgsVectorLayer.SetSelection)
        municipi_name = ''
        for municipi in self.dic_municipi_table.getSelectedFeatures():
            municipi_name = municipi['nom_muni']

        return municipi_name

    def write_mm_report(self):
        """  """
        with open(self.report_path, "w") as f:
            f.write('#########################\n')
            f.write('Llistat de municipis preparats per generar el seu Mapa Municipal\n')
            f.write(f'Data - {self.current_date}\n')
            f.write('#########################\n\n')

            mm_count = 0
            for muni_ine, muni_name in self.municipi_dict.items():
                f.write(f'{muni_ine} -- {muni_name}\n')
                mm_count += 1

            f.write(f'\nHi ha un total de {str(mm_count)} MM nous per generar\n')
            f.write('#########################')

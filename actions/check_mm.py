# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the CheckMM class is defined. The main function
of this class is to check whether exist any municipality ready to make its Municipal
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
                       QgsVectorLayerJoinInfo,
                       QgsMessageLog,
                       Qgis)

from ..config import *
from .adt_postgis_connection import PgADTConnection


class CheckMM:
    """ Municipal Map checker class """

    def __init__(self):
        """ Constructor """
        # Initialize instance attributes
        # Common
        self.current_date = datetime.now().strftime("%Y%m%d")
        self.municipality_dict = {}
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        # Log
        self.report_path = os.path.join(CHECK_MM_LOCAL_DIR, f'Nous_MM_{self.current_date}.txt')
        # Entities
        self.area_muni_cat_table = self.pg_adt.get_table('area_muni_cat')
        self.line_table = self.pg_adt.get_table('linia')
        self.dic_municipality_table = self.pg_adt.get_table('dic_municipality')
        self.mapa_muni_table = self.pg_adt.get_table('mapa_muni_icc')
        self.mtt_table = self.pg_adt.get_table('memoria_treb_top')

    def get_new_mm(self):
        """
        Main entry point. Inspects the database and gets a list of the municipalities which their Municipality can
        be done. Then writes that list in a text file.
        """
        QgsMessageLog.logMessage('Comprovant llistat de nous Mapes municipals...', level=Qgis.Info)
        for municipality in self.area_muni_cat_table.getFeatures():
            municipality_ine = municipality['codi_muni']
            # Check if the municipality has a considered MM
            municipality_mm_exists = self.check_municipality_mm(municipality_ine)
            if not municipality_mm_exists:
                municipality_id = municipality['id_area']
                # Get municipality boundary lines list
                municipality_line_list = self.get_municipality_lines(municipality_id)
                municipality_mm_ready = self.check_lines_mtt(municipality_line_list)
                if municipality_mm_ready:
                    municipality_name = self.get_municipality_name(municipality_ine)
                    self.municipality_dict[municipality_ine] = municipality_name

        self.write_mm_report()
        QgsMessageLog.logMessage('Nous Mapes municipals comprovats', level=Qgis.Info)

    def check_municipality_mm(self, municipality_ine):
        """ Check if the municipality already exists in the database

        :param municipality_ine: INE ID of the municipality
        :type municipality_ine: str

        :return: Indicates if the municipality is in the database or not
        :rtype: bool
        """
        self.mapa_muni_table.selectByExpression(f'"codi_muni"=\'{municipality_ine}\' and "vig_mm" is True', QgsVectorLayer.SetSelection)
        count = self.mapa_muni_table.selectedFeatureCount()
        self.mapa_muni_table.removeSelection()
        if count == 1:
            return True
        else:
            return False

    def get_municipality_lines(self, municipality_id):
        """
        Get all the boundary lines' ID of the municipality

        :param municipality_id: ID of the municipality
        :type municipality_id: str

        :return: municipality_line_list: List with the ID of the boundary lines that make the municipality
        :rtype: tuple
        """
        self.line_table.selectByExpression(f'"id_area_1"={municipality_id} or "id_area_2"={municipality_id}',
                                                QgsVectorLayer.SetSelection)
        municipality_line_list = []
        for line in self.line_table.getSelectedFeatures():
            line_id = line['id_linia']
            municipality_line_list.append(int(line_id))

        self.line_table.removeSelection()
        return municipality_line_list

    def check_lines_mtt(self, municipality_lines_list):
        """
        Check if the boundary lines are official

        :param municipality_lines_list: List with the ID of the boundary lines that make the municipality
        :type municipality_lines_list: tuple

        :return: municipality_mm: Indicates if the map can be done for that municipality
        :rtype: bool
        """
        municipality_mm = True
        for line_id in municipality_lines_list:
            self.mtt_table.selectByExpression(f'"id_linia"={line_id} and "vig_mtt" is True', QgsVectorLayer.SetSelection)
            count = self.mtt_table.selectedFeatureCount()
            self.mtt_table.removeSelection()
            if count == 0:
                municipality_mm = False

        return municipality_mm

    def get_municipality_name(self, municipality_ine):
        """
        Get the name of the municipality

        :param municipality_ine: INE ID of the municipality
        :type municipality_ine: str

        :return: municipality name: Name of the municipality
        :rtype: str
        """
        self.dic_municipality_table.selectByExpression(f'"codi_muni"=\'{municipality_ine}\'',
                                                    QgsVectorLayer.SetSelection)
        municipality_name = ''
        for municipality in self.dic_municipality_table.getSelectedFeatures():
            municipality_name = municipality['nom_muni']

        return municipality_name

    def write_mm_report(self):
        """  """
        with open(self.report_path, "w") as f:
            f.write('#########################\n')
            f.write('Llistat de municipis preparats per generar el seu Mapa Municipal\n')
            f.write(f'Data - {self.current_date}\n')
            f.write('#########################\n\n')

            mm_count = 0
            for muni_ine, muni_name in self.municipality_dict.items():
                f.write(f'{muni_ine} -- {muni_name}\n')
                mm_count += 1

            f.write(f'\nHi ha un total de {str(mm_count)} MM nous per generar\n')
            f.write('#########################')

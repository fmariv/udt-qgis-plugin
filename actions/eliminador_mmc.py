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
import numpy as np

from qgis.core import QgsVectorLayer
from qgis.core.additions.edit import edit
from PyQt5.QtWidgets import QMessageBox

from ..config import *
from ..utils import *
from .adt_postgis_connection import PgADTConnection


class EliminadorMMC:
    """ MMC Deletion class """

    def __init__(self, municipi_id, coast=False):
        # Common
        self.arr_nom_municipis = np.genfromtxt(DIC_NOM_MUNICIPIS, dtype=None, encoding=None, delimiter=';', names=True)
        self.arr_lines_data = np.genfromtxt(DIC_LINES, dtype=None, encoding=None, delimiter=';', names=True)
        # ADT PostGIS connection
        self.pg_adt = PgADTConnection(HOST, DBNAME, USER, PWD, SCHEMA)
        self.pg_adt.connect()
        # ###
        # Input dependant that don't need data from the layers
        self.municipi_id = int(municipi_id)
        self.coast = coast
        self.municipi_codi_ine = self.get_municipi_codi_ine(self.municipi_id)
        self.municipi_lines = self.get_municipi_lines()   # Get a list with all the lines ID
        if self.coast:
            self.municipi_coast_line = self.get_municipi_coast_line()
        # Input layers
        self.input_points_layer, self.input_lines_layer, self.input_polygons_layer, self.input_coast_lines_layer, self.input_full_bt5_table, self.input_points_table, self.input_line_table, self.input_coast_line_table = (None,) * 8

    def get_municipi_codi_ine(self, municipi_id):
        """
        Get the municipi INE ID
        :param municipi_id -> ID of the municipi which to obtain its INE ID
        :return: codi_ine -> INE ID of the municipi
        """
        muni_data = self.arr_nom_municipis[np.where(self.arr_nom_municipis['id_area'] == f'"{municipi_id}"')]
        if muni_data:
            codi_ine = muni_data['codi_ine_muni'][0].strip('"')

            return codi_ine

    def get_municipi_lines(self):
        """
        Get all the municipal boundary lines that make the input municipi
        :return lines_muni_list -> List with all the boundary lines that make the municipi
        """
        lines_muni_1 = self.arr_lines_data[np.where(self.arr_lines_data['CODIMUNI1'] == self.municipi_id)]
        lines_muni_2 = self.arr_lines_data[np.where(self.arr_lines_data['CODIMUNI2'] == self.municipi_id)]
        lines_muni_1_list = lines_muni_1['IDLINIA'].tolist()
        lines_muni_2_list = lines_muni_2['IDLINIA'].tolist()

        lines_muni_list = lines_muni_1_list + lines_muni_2_list

        return lines_muni_list

    def check_mm_exists(self, municipi_codi_ine, layer='postgis'):
        """
        Check if the input municipi exists as a Municipal Map into the database or into the input polygon layer.
        :param municipi_codi_ine -> Municipi INE ID of the municipi to check if exists its MM
        :param layer -> Layer into check if the MM exists
        :return Boolean True/False -> Boolean that means if the MM exists into the given layer or not
        """
        mapa_muni_table, expression = None, None
        if layer == 'postgis':
            mapa_muni_table = self.pg_adt.get_table('mapa_muni_icc')
            expression = f'"codi_muni"=\'{municipi_codi_ine}\' and "vig_mm" is True'
        elif layer == 'input':
            mapa_muni_table = self.input_polygons_layer
            expression = f'"CodiMuni"=\'{municipi_codi_ine}\''

        mapa_muni_table.selectByExpression(expression, QgsVectorLayer.SetSelection)
        count = mapa_muni_table.selectedFeatureCount()
        if count == 0:
            return False
        else:
            return True

    def get_municipi_coast_line(self):
        """
        Get the municipi coast line, if exists
        :return coast_line_id -> ID of the coast boundary line
        """
        coast_line_id = ''
        for line_id in self.municipi_lines:
            line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]
            if line_data['LIMCOSTA'] == 'S':
                coast_line_id = line_id

        return coast_line_id

    def remove_municipi_data(self):
        """
        Main entry point. This function removes all the data of the municipi that the user wants to remove
        from the database.
        """
        self.set_layers()
        self.remove_polygons()
        self.remove_lines_layer()
        self.remove_lines_table()
        self.remove_points_layer()
        self.remove_points_table()
        if self.coast:
            self.remove_coast_line_layer()
            self.remove_coast_lines_table()
            self.remove_full_bt5m()

    def set_layers(self):
        """ Set the paths of the working vector layers """
        directory_list = os.listdir(ELIMINADOR_WORK_DIR)
        directory_path = os.path.join(ELIMINADOR_WORK_DIR, directory_list[0])
        shapefiles_list = os.listdir(directory_path)

        for shapefile in shapefiles_list:
            if '-fita-' in shapefile and shapefile.endswith('.shp'):
                self.input_points_layer = QgsVectorLayer(os.path.join(directory_path, shapefile))
            elif '-liniaterme-' in shapefile and shapefile.endswith('.shp'):
                self.input_lines_layer = QgsVectorLayer(os.path.join(directory_path, shapefile))
            elif '-poligon-' in shapefile and shapefile.endswith('.shp'):
                self.input_polygons_layer = QgsVectorLayer(os.path.join(directory_path, shapefile))
            elif '-liniacosta-' in shapefile and shapefile.endswith('.shp'):
                self.input_coast_lines_layer = QgsVectorLayer(os.path.join(directory_path, shapefile))
            elif '-liniacostataula-' in shapefile and shapefile.endswith('.dbf'):
                self.input_coast_line_table = QgsVectorLayer(os.path.join(directory_path, shapefile))
            elif '-tallfullbt5m-' in shapefile and shapefile.endswith('.dbf'):
                self.input_full_bt5_table = QgsVectorLayer(os.path.join(directory_path, shapefile))
            elif '-liniatermetaula-' in shapefile and shapefile.endswith('.dbf'):
                self.input_line_table = QgsVectorLayer(os.path.join(directory_path, shapefile))
            elif '-fitataula-' in shapefile and shapefile.endswith('.dbf'):
                self.input_points_table = QgsVectorLayer(os.path.join(directory_path, shapefile))

    def remove_polygons(self):
        """ Remove the municipi's polygons from the database """
        self.input_polygons_layer.selectByExpression(f'"CodiMuni"=\'{self.municipi_codi_ine}\'',
                                                     QgsVectorLayer.SetSelection)
        with edit(self.input_polygons_layer):
            for polygon in self.input_polygons_layer.getSelectedFeatures():
                self.input_polygons_layer.deleteFeature(polygon.id())

    def remove_coast_line_layer(self):
        """ Remove the municipi's coast lines from the database's layer """
        # 5065
        self.input_coast_lines_layer.selectByExpression(f'"IdLinia"={self.municipi_coast_line}',
                                                        QgsVectorLayer.SetSelection)
        with edit(self.input_coast_lines_layer):
            for line in self.input_coast_lines_layer.getSelectedFeatures():
                self.input_coast_lines_layer.deleteFeature(line.id())

    def remove_full_bt5m(self):
        """ Remove the municipi's BT5M full from the database's table """
        self.input_full_bt5_table.selectByExpression(f'"IdLinia"={self.municipi_coast_line}',
                                                     QgsVectorLayer.SetSelection)
        with edit(self.input_full_bt5_table):
            for line in self.input_full_bt5_table.getSelectedFeatures():
                self.input_full_bt5_table.deleteFeature(line.id())

    def remove_points_layer(self):
        """
        Remove the municipi's points from the database's layer
        Atenció: en alguns casos no esborra correctament les fites 3 termes.
        """
        point_id_remove_list = self.get_points_to_remove()
        with edit(self.input_points_layer):
            for point_id in point_id_remove_list:
                self.input_points_layer.selectByExpression(f'"IdFita"=\'{point_id}\'', QgsVectorLayer.SetSelection)
                for feature in self.input_points_layer.getSelectedFeatures():
                    self.input_points_layer.deleteFeature(feature.id())

        box = QMessageBox()
        box.setIcon(QMessageBox.Warning)
        box.setText("Enrecorda't de revisar que s'han esborrat\ncorrectament totes les fites 3 termes.")
        box.exec_()

    def get_points_to_remove(self):
        """
        Get the points that the class has to remove, in order to avoid removing points that have to exists
        due they also pertain to another municipi that have MM.
        :return point_id_remove_list -> List with the ID of all the points to remove from the points layer
        """
        fita_mem_layer = self.pg_adt.get_layer('v_fita_mem', 'id_fita')
        point_id_remove_list = []
        delete_lines_list, edit_lines_dict = self.get_lines_to_manage()

        for line_id in delete_lines_list:
            fita_mem_layer.selectByExpression(f'"id_linia"=\'{line_id}\'', QgsVectorLayer.SetSelection)
            for feature in fita_mem_layer.getSelectedFeatures():
                # Check that the point has correctly filled the coordinates fields
                if feature['point_x'] and feature['point_y']:
                    point_id_fita = coordinates_to_id_fita(feature['point_x'], feature['point_y'])
                    if feature['num_termes'] == 'F2T':
                        point_id_remove_list.append(point_id_fita)
                    elif feature['num_termes'] != 'F2T' and feature['num_termes']:
                        '''
                        No es pot fer una selecció espacial fita - linia de terme, de manera que no es 
                        pot comprovar de manera 100% fiable si una fita 3 termes té una línia veïna amb MM o no.
                        El que es fa és el següent:
                            1. Per cada línia veïna, saber si cap dels municipis de la línia de terme té MM al MMC.
                            2. Si en té, no s'elimina la fita 3 termes.
                        '''
                        neighbor_lines = self.get_neighbor_lines(line_id)
                        neighbor_mm = False
                        for neighbor_line in neighbor_lines:
                            # Get neighbors municipis
                            neighbor_municipi_1_codi_ine, neighbor_municipi_2_codi_ine = self.get_neighbors_ine(
                                neighbor_line)
                            # Check if any of neighbors has MM
                            neighbor_municipi_1_mm = self.check_mm_exists(neighbor_municipi_1_codi_ine, 'input')
                            neighbor_municipi_2_mm = self.check_mm_exists(neighbor_municipi_2_codi_ine, 'input')
                            if (neighbor_municipi_1_mm or neighbor_municipi_2_mm) and not neighbor_mm:
                                neighbor_mm = True

                        # If there is not any neighbor municipi with MM, remove the point
                        if not neighbor_mm:
                            point_id_remove_list.append(point_id_fita)

        return point_id_remove_list

    def remove_points_table(self):
        """ Remove the municipi's points from the database's table """
        for line_id in self.municipi_lines:
            with edit(self.input_points_table):
                line_id_txt = line_id_2_txt(line_id)
                self.input_points_table.selectByExpression(f'"IdLinia"=\'{line_id_txt}\'', QgsVectorLayer.SetSelection)
                for feature in self.input_points_table.getSelectedFeatures():
                    self.input_points_table.deleteFeature(feature.id())

    def get_neighbor_lines(self, line_id):
        """
        Get the neighbor lines from the given boundary line
        :param line_id -> ID of the line to obtain its neighbor boundary lines
        :return neighbor_lines -> List with the line ID of the neighbor lines
        """
        neighbor_lines = []
        linia_veina_table = self.pg_adt.get_table('linia_veina')
        linia_veina_table.selectByExpression(f'"id_linia"=\'{line_id}\'', QgsVectorLayer.SetSelection)
        for line in linia_veina_table.getSelectedFeatures():
            neighbor_lines.append(int(line['id_linia_veina']))

        return neighbor_lines

    def remove_lines_layer(self):
        """ Remove the municipi's boundary lines from the database's layer """
        # Remove boundary lines
        delete_lines_list, edit_lines_dict = self.get_lines_to_manage()
        if delete_lines_list:
            with edit(self.input_lines_layer):
                for line_id in delete_lines_list:
                    self.input_lines_layer.selectByExpression(f'"IdLinia"=\'{line_id}\'', QgsVectorLayer.SetSelection)
                    for line in self.input_lines_layer.getSelectedFeatures():
                        self.input_lines_layer.deleteFeature(line.id())

        # Edit boundary lines
        if edit_lines_dict:
            with edit(self.input_lines_layer):
                for line_id, dates in edit_lines_dict.items():
                    neighbor_valid_de, neighbor_data_alta, neighbor_ine = dates
                    self.input_lines_layer.selectByExpression(f'"IdLinia"=\'{line_id}\'', QgsVectorLayer.SetSelection)
                    for line in self.input_lines_layer.getSelectedFeatures():
                        if line['ValidDe'] < neighbor_valid_de:
                            line['ValidDe'] = neighbor_valid_de
                            self.input_lines_layer.updateFeature(line)
                        if line['DataAlta'] < neighbor_data_alta:
                            line['DataAlta'] = neighbor_data_alta
                            self.input_lines_layer.updateFeature(line)

    def get_lines_to_manage(self):
        """
        Get a list with the line id of the lines to remove and a dict with the line id and some dates of the lines
        to edit
        :return delete_lines_list -> List with the line ID of the lines to remove
        :return edit_lines_dict -> List with the line ID and the Valid De, Data Alta and INE ID of the neighbor municipi
        """
        delete_lines_list = []
        edit_lines_dict = {}
        for line_id in self.municipi_lines:
            # Check if the other municipi has a considered MM
            neighbor_ine = self.get_neighbor_ine(line_id)
            neighbor_mm = self.check_mm_exists(neighbor_ine, 'input')
            line_id_txt = line_id_2_txt(line_id)
            # If the neighbor municipi doesn't have a considered MM, directly remove the boundary line
            # If it has, create a dictionary with its Data Alta and Valid De to check if it has to replace the dates
            if not neighbor_mm:
                delete_lines_list.append(line_id_txt)
            else:
                neighbor_data_alta, neighbor_valid_de = self.get_neighbor_dates(neighbor_ine)
                edit_lines_dict[line_id_txt] = [neighbor_valid_de, neighbor_data_alta, neighbor_ine]

        return delete_lines_list, edit_lines_dict

    def get_neighbor_municipi(self, line_id):
        """
        Get the ID of the neighbor municipi
        :return neighbor_municipi_id -> ID of the neighbor municipi
        """
        line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]
        neighbor_municipi_id = ''
        if line_data['CODIMUNI1'] == self.municipi_id:
            neighbor_municipi_id = line_data['CODIMUNI2'][0]
        elif line_data['CODIMUNI2'] == self.municipi_id:
            neighbor_municipi_id = line_data['CODIMUNI1'][0]

        return neighbor_municipi_id

    def get_neighbors_municipis(self, line_id):
        """
        Get the IDs of both municipis than share a boundary line
        :return neighbor_municipi_1_id -> ID of the first neighbor municipi
        :return neighbor_municipi_2_id -> ID of the second neighbor municipi
        """
        line_data = self.arr_lines_data[np.where(self.arr_lines_data['IDLINIA'] == line_id)]
        neighbor_municipi_1_id, neighbor_municipi_2_id = line_data['CODIMUNI1'][0], line_data['CODIMUNI2'][0]

        return neighbor_municipi_1_id, neighbor_municipi_2_id

    def get_neighbor_ine(self, line_id):
        """
        Get the INE ID of the neighbor municipi
        :return neighbor_municipi_codi_ine -> INE ID of the neighbor municipi
        """
        neighbor_municipi_id = self.get_neighbor_municipi(line_id)
        neighbor_municipi_codi_ine = self.get_municipi_codi_ine(neighbor_municipi_id)

        return neighbor_municipi_codi_ine

    def get_neighbors_ine(self, line_id):
        """
        Get the INE IDs of both municipis than share a boundary line
        :return neighbor_municipi_1_codi_ine -> INE ID of the first neighbor municipi
        :return neighbor_municipi_2_codi_ine -> INE ID of the second neighbor municipi
        """
        neighbor_municipi_1_id, neighbor_municipi_2_id = self.get_neighbors_municipis(line_id)
        neighbor_municipi_1_codi_ine = self.get_municipi_codi_ine(neighbor_municipi_1_id)
        neighbor_municipi_2_codi_ine = self.get_municipi_codi_ine(neighbor_municipi_2_id)

        return neighbor_municipi_1_codi_ine, neighbor_municipi_2_codi_ine

    def get_neighbor_dates(self, neighbor_ine):
        """
        Get the Data Alta and Valid De dates of the neighbor municipi
        :return data_alta -> Data Alta of the neighbor municipi
        :return valid_de -> Valid De of the neighbor municipi
        """
        self.input_polygons_layer.selectByExpression(f'"CodiMuni"=\'{neighbor_ine}\'',
                                                     QgsVectorLayer.SetSelection)
        data_alta, valid_de = None, None
        for polygon in self.input_polygons_layer.getSelectedFeatures():
            data_alta = polygon['DataAlta']
            valid_de = polygon['ValidDe']

        return data_alta, valid_de

    def remove_lines_table(self):
        """ Remove the municipi's boundary lines from the database's table """
        with edit(self.input_line_table):
            for line in self.municipi_lines:
                line_txt = line_id_2_txt(line)
                self.input_line_table.selectByExpression(f'"IdLinia"={line_txt} and "CodiMuni" = \'{self.municipi_codi_ine}\'',
                                                         QgsVectorLayer.SetSelection)
                for feature in self.input_line_table.getSelectedFeatures():
                    self.input_line_table.deleteFeature(feature.id())

    def remove_coast_lines_table(self):
        """ Remove the municipi's boundary coast line from the database's table """
        with edit(self.input_coast_line_table):
            self.input_coast_line_table.selectByExpression(f'"IdLinia"={self.municipi_coast_line}')
            for feature in self.input_coast_line_table.getSelectedFeatures():
                self.input_coast_line_table.deleteFeature(feature.id())


def check_eliminador_input_data():
    """ Check if the module has all the necessary input data into the input directory
    :return Boolean True/False -> Boolean that means if the input data exists into the input directory or not
    """

    box = QMessageBox()
    box.setIcon(QMessageBox.Critical)
    directory_list = os.listdir(ELIMINADOR_WORK_DIR)

    # Check that exists the input directory
    if not directory_list:
        box.setText("No hi ha cap carpeta de MMC a la carpeta d'entrades.")
        box.exec_()
        return False
    # Check that only exists one input directory
    if len(directory_list) > 1:
        box.setText("Hi ha més d'una carpeta de MMC a la carpeta d'entrades.")
        box.setText("Si us plau, esborra les que no siguin necessàries.")
        box.exec_()
        return False
    # Check that exists the input shapefiles
    directory_path = os.path.join(ELIMINADOR_WORK_DIR, directory_list[0])
    shapefiles_list = os.listdir(directory_path)
    shapefiles_count = 0
    for shapefile in shapefiles_list:
        if ('-fita-' in shapefile or '-liniacosta-' in shapefile or '-liniacostataula-' in shapefile or '-liniaterme-' in shapefile or '-liniatermetaula-' in shapefile or '-poligon-' in shapefile or '-tallfullbt5m-' in shapefile)\
                and shapefile.endswith('.dbf'):
            shapefiles_count += 1

    if shapefiles_count == 7:
        return True
    else:
        box.setText("Falten shapefiles del MMC a la carpeta d'entrades.\nSi us plau, revisa-ho.")
        box.exec_()
        return False

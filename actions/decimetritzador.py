# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the decimetritzador class is defined. The main function
of this class is to take both points and lines layers and transform them
decimals in order to round them to 1.
***************************************************************************/
"""

import os

from ..utils import *

from qgis.core.additions.edit import edit
from qgis.core import (QgsVectorLayer,
                       QgsDataSourceUri,
                       QgsProviderRegistry,
                       QgsPoint,
                       QgsPointXY,
                       QgsGeometry,
                       QgsMessageLog,
                       Qgis)
from PyQt5.QtWidgets import QMessageBox


class Decimetritzador:

    def __init__(self, doc_delim_directory):
        # Layers and paths
        self.doc_delim = doc_delim_directory
        self.point_layer, self.line_layer = None, None
        # Message box
        self.box_error = QMessageBox()
        self.box_error.setIcon(QMessageBox.Critical)

    def decimetritzar(self):
        """ Main entry point of the Decimetritzador's class where  """
        self.set_layers()
        self.decimetritzar_points()
        self.decimetritzar_lines()

    def set_layers(self):
        """ Set the input layers as PyQGIS Vector layers """
        self.point_layer = QgsVectorLayer(os.path.join(self.doc_delim, 'Cartografia', 'Punt.shp'))
        self.line_layer = QgsVectorLayer(os.path.join(self.doc_delim, 'Cartografia', 'Lin_TramPpta.shp'))
        if self.line_layer.featureCount() == 0:
            self.line_layer = QgsVectorLayer(os.path.join(self.doc_delim, 'Cartografia', 'Lin_Tram.shp'))
            QgsMessageLog.logMessage('Es decimetritzarà la capa Lin_Tram', level=Qgis.Info)
        else:
            QgsMessageLog.logMessage('Es decimetritzarà la capa Lin_TramPpta', level=Qgis.Info)

    def decimetritzar_points(self):
        """ Edit the points' geometry in order to round the coordinates decimals """
        QgsMessageLog.logMessage('Decimetritzant capa de punts...', level=Qgis.Info)
        with edit(self.point_layer):
            for point in self.point_layer.getFeatures():
                geom = point.geometry()
                coord_x = geom.get().x()
                coord_y = geom.get().y()
                z = geom.get().z()
                # Round coordinates
                x, y = round_coordinates(coord_x, coord_y)
                if z != 0.0:
                    z = round(z, 1)
                # Create new geometry
                rounded_point = QgsPoint(x, y, z)
                rounded_geom = QgsGeometry(rounded_point)
                # Set new geometry
                self.point_layer.changeGeometry(point.id(), rounded_geom)
        QgsMessageLog.logMessage('Capa de punts decimetritzada', level=Qgis.Info)

    def decimetritzar_lines(self):
        """ Edit the lines' geometry in order to round the endpoint's coordinates decimals """
        QgsMessageLog.logMessage('Decimetritzant capa de trams de línia...', level=Qgis.Info)
        with edit(self.line_layer):
            for line in self.line_layer.getFeatures():
                tram = line.geometry().asMultiPolyline()
                verts = tram[0]
                # Comprovar si el primer i últim vertex del tram ja estan decimetritzats i per tant no s'han
                # de decimetritzar
                first_vert_decim, last_vert_decim = self.check_tram_decimals(verts)
                if first_vert_decim and last_vert_decim:
                    continue
                first_vertex = verts[0]
                last_vertex = verts[-1]
                if len(verts) > 2:
                    if first_vert_decim and not last_vert_decim:
                        tram_vertex = verts[:-1]
                    elif not first_vert_decim and last_vert_decim:
                        tram_vertex = verts[1:]
                    else:
                        tram_vertex = verts[1:-1]
                # Round first and last vertex
                # First
                if not first_vert_decim:
                    first_coord_x = first_vertex.x()
                    first_coord_y = first_vertex.y()
                    first_x, first_y = round_coordinates(first_coord_x, first_coord_y)
                    rounded_first_vert = QgsPointXY(first_x, first_y)
                # Last
                if not last_vert_decim:
                    last_coord_x = last_vertex.x()
                    last_coord_y = last_vertex.y()
                    last_x, last_y = round_coordinates(last_coord_x, last_coord_y)
                    rounded_last_vert = QgsPointXY(last_x, last_y)
                # Create new geometry
                if len(verts) > 2:
                    if not first_vert_decim:
                        tram_vertex.insert(0, rounded_first_vert)
                    if not last_vert_decim:
                        tram_vertex.insert(len(tram_vertex), rounded_last_vert)
                    rounded_geom = QgsGeometry.fromMultiPolylineXY([tram_vertex])
                else:
                    pairs_vertex = [rounded_first_vert, rounded_last_vert]
                    rounded_geom = QgsGeometry.fromMultiPolylineXY([pairs_vertex])

                # Set new geometry
                self.line_layer.changeGeometry(line.id(), rounded_geom)
        QgsMessageLog.logMessage('Capa de trams de línia decimetritzada', level=Qgis.Info)

    @staticmethod
    def check_tram_decimals(verts):
        """ Check if a line's endpoints have them coordinates decimals already rounded or not """
        first_vertex = verts[0]
        last_vertex = verts[-1]
        # Check first
        first_coord_x = first_vertex.x()
        first_coord_y = first_vertex.y()
        first_dif_x = abs(first_coord_x - round(first_coord_x, 1))
        first_dif_y = abs(first_coord_y - round(first_coord_y, 1))
        # Check last
        last_coord_x = last_vertex.x()
        last_coord_y = last_vertex.y()
        last_dif_x = abs(last_coord_x - round(last_coord_x, 1))
        last_dif_y = abs(last_coord_y - round(last_coord_y, 1))
        # Check
        if (first_dif_x > 0.0001 or first_dif_y > 0.0001) and (last_dif_x > 0.0001 or last_dif_y > 0.0001):
            return False, False
        elif (first_dif_x > 0.0001 or first_dif_y > 0.0001) and (last_dif_x < 0.01 or last_dif_y < 0.01):
            return False, True
        elif (first_dif_x < 0.01 or first_dif_y < 0.01) and (last_dif_x > 0.0001 or last_dif_y > 0.0001):
            return True, False
        else:
            return True, True

    def check_input_data(self):
        """ Check that exists all the necessary input data into the input directory """
        cartography_directory = os.path.join(self.doc_delim, 'Cartografia')
        if os.path.isdir(cartography_directory):
            points_layer = os.path.join(cartography_directory, 'Punt.shp')
            lines_layer = os.path.join(cartography_directory, 'Lin_TramPpta.shp')
            if os.path.exists(points_layer) and os.path.exists(lines_layer):
                return True
            else:
                self.box_error.setText("Falta la capa de Punts o Trams a la carpeta de Cartografia")
                self.box_error.exec_()
                return False
        else:
            self.box_error.setText("El directori introduït no té carpeta de Cartografia")
            self.box_error.exec_()
            return False


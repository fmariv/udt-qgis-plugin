# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the ManagePoligonal class is defined. The main function
of this class is to run the automation process that updates the poligonal table
with the poligonal's point layer reprojected ETRS89 coordinates.
***************************************************************************/
"""

import os

from qgis.core import (QgsVectorLayer,
                       QgsField,
                       QgsMessageLog,
                       QgsVectorLayerJoinInfo)
import processing
from PyQt5.QtWidgets import QMessageBox
from qgis.core.additions.edit import edit
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QMessageBox

from ..config import *


# TODO TEST

class ManagePoligonal:

    def __init__(self, doc_delim_directory):
        # Layers and paths
        self.doc_delim = doc_delim_directory
        self.polig_points_layer, self.polig_table, self.join_object = None, None, None
        # Message box
        self.box_error = QMessageBox()
        self.box_error.setIcon(QMessageBox.Critical)

    def update_poligonal_table(self):
        """   """
        self.set_layers()
        self.add_fields()
        self.populate_fields()
        self.join()
        self.update()
        self.polig_table.removeJoin(self.join_object.joinLayerId)
        self.remove_fields()

    def set_layers(self):
        """  """
        self.polig_points_layer = QgsVectorLayer(os.path.join(self.doc_delim, 'Cartografia/Pto_Polig.shp'))
        self.polig_table = QgsVectorLayer(os.path.join(self.doc_delim, 'Taules/POLIGONA.dbf'))

    # #######################
    # Add fields
    def add_fields(self):
        """  """
        self.add_fields_layer()
        self.add_fields_table()

    def add_fields_layer(self):
        """  """
        concat_field = QgsField(name='Concat_1', type=QVariant.String, typeName='text', len=12)
        x_coord_field = QgsField(name='X_Coord', type=QVariant.Double, len=19, prec=5)
        y_coord_field = QgsField(name='Y_Coord', type=QVariant.Double, len=19, prec=5)

        new_fields_list = (x_coord_field, y_coord_field, concat_field)
        self.polig_points_layer.dataProvider().addAttributes(new_fields_list)
        self.polig_points_layer.updateFields()

    def add_fields_table(self):
        """  """
        concat_field = QgsField(name='Concat_2', type=QVariant.String, typeName='text', len=12)

        self.polig_table.dataProvider().addAttributes([concat_field])
        self.polig_table.updateFields()

    # #######################
    # Populate fields
    def populate_fields(self):
        """  """
        self.populate_fields_layer()
        self.populate_fields_table()

    def populate_fields_layer(self):
        """  """
        with edit(self.polig_points_layer):
            fields = self.polig_points_layer.fields()
            for feature in self.polig_points_layer.getFeatures():
                concat = f"{feature['ID_POLIG']}_{int(feature['ID_VIS'])}"
                x_coord = round(feature.geometry().asPoint()[0], 5)
                y_coord = round(feature.geometry().asPoint()[1], 5)
                attrs = {
                    fields.indexFromName("X_Coord"): x_coord,
                    fields.indexFromName("Y_Coord"): y_coord,
                    fields.indexFromName("Concat_1"): concat
                }
                self.polig_points_layer.dataProvider().changeAttributeValues({feature.id(): attrs})

    def populate_fields_table(self):
        """  """
        with edit(self.polig_table):
            fields = self.polig_table.fields()
            id_field = fields.indexFromName("Concat_2")
            for feature in self.polig_table.getFeatures():
                concat = f"{feature['ID_POLIG']}_{int(feature['ID_VIS'])}"
                attr = {id_field: concat}
                self.polig_table.dataProvider().changeAttributeValues({feature.id(): attr})

    # #######################
    # Join
    def join(self):
        """  """
        # Join parameters
        self.join_object = QgsVectorLayerJoinInfo()
        self.join_object.joinLayerId = self.polig_points_layer.id()
        self.join_object.joinFieldName = 'Concat_1'
        self.join_object.targetFieldName = 'Concat_2'
        self.join_object.setJoinLayer(self.polig_points_layer)
        self.join_object.memoryCache = True

        # Perform join
        self.polig_table.addJoin(self.join_object)

    # #######################
    # Update
    def update(self):
        """  """
        # Fields parameters
        field_names = [field.name() for field in self.polig_table.fields()]
        for field in field_names:
            QgsMessageLog.logMessage(field)

        fields = self.polig_table.fields()
        id_x_comp = fields.indexFromName("X_COMP")
        id_y_comp = fields.indexFromName("Y_COMP")
        id_x_conv = fields.indexFromName("X_CONV")
        id_y_conv = fields.indexFromName("Y_CONV")

        with edit(self.polig_table):
            # Compensades
            self.polig_table.selectByExpression('"X_COMP" != 0')
            for feature in self.polig_table.getSelectedFeatures():
                new_x_coord = feature['_X_Coord']
                new_y_coord = feature['_Y_Coord']
                comp_attrs = {
                    id_x_comp: new_x_coord,
                    id_y_comp: new_y_coord
                }
                self.polig_table.dataProvider().changeAttributeValues({feature.id(): comp_attrs})

            # No compensades
            self.polig_table.invertSelection()
            for feature in self.polig_table.getSelectedFeatures():
                new_x_coord = feature['_X_Coord']
                new_y_coord = feature['_Y_Coord']
                conv_attrs = {
                    id_x_conv: new_x_coord,
                    id_y_conv: new_y_coord
                }
                self.polig_table.dataProvider().changeAttributeValues({feature.id(): conv_attrs})

    # #######################
    # Remove fields
    def remove_fields(self):
        """  """
        self.remove_fields_layer()
        self.remove_fields_table()

    def remove_fields_layer(self):
        """  """
        fields = self.polig_points_layer.fields()
        delete_fields_list = list((fields.indexFromName("X_Coord"), fields.indexFromName("Y_Coord"), fields.indexFromName("Concat_1")))

        with edit(self.polig_points_layer):
            self.polig_points_layer.dataProvider().deleteAttributes(delete_fields_list)

    def remove_fields_table(self):
        """  """
        fields = self.polig_table.fields()
        delete_field = fields.indexFromName("Concat_2")

        with edit(self.polig_table):
            self.polig_table.dataProvider().deleteAttributes([delete_field])

    # #######################
    # Check
    def check_input_data(self):
        """ Check that exists all the necessary input data into the input directory """
        cartography_directory = os.path.join(self.doc_delim, 'Cartografia')
        tables_directory = os.path.join(self.doc_delim, 'Taules')

        # Check polig points layer
        if os.path.isdir(cartography_directory):
            polig_points_layer = os.path.join(cartography_directory, 'Pto_Polig.shp')
            if not os.path.exists(polig_points_layer):
                self.box_error.setText("Falta la capa de Punts de poligonal a la carpeta de Cartografia")
                self.box_error.exec_()
                return False
        else:
            self.box_error.setText("El directori introduït no té carpeta de Cartografia")
            self.box_error.exec_()
            return False

        # Check polig table
        if os.path.isdir(tables_directory):
            polig_table = os.path.join(tables_directory, 'POLIGONA.dbf')
            if not os.path.exists(polig_table):
                self.box_error.setText("Falta la taula POLIGONA a la carpeta de Taules")
                self.box_error.exec_()
                return False
        else:
            self.box_error.setText("El directori introduït no té carpeta de Taules")
            self.box_error.exec_()
            return False

        return True

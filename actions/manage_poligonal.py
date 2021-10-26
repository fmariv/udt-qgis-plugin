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
                       QgsVectorLayerJoinInfo,
                       QgsMessageLog,
                       Qgis)
from qgis.core.additions.edit import edit
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QMessageBox


class ManagePoligonal:
    """ Poligonal managing class """

    def __init__(self, doc_delim_directory):
        # Layers and paths
        self.doc_delim = doc_delim_directory
        self.polig_points_layer, self.polig_table, self.join_object = None, None, None
        # Message box
        self.box_error = QMessageBox()
        self.box_error.setIcon(QMessageBox.Critical)

    def update_poligonal_table(self):
        """
        Main entry point where the poligonal gets updated, which means that the poligonal's points coordinates
        of the POLIGONA.dbf table get reprojected from ED50 to ETRS88.
        The method only updates the attributes X/Y COMP and X/Y CONV.
        """
        QgsMessageLog.logMessage('Procés iniciat: actualització de la Poligonal', level=Qgis.Info)
        self.set_layers()
        self.add_fields()
        self.populate_fields()
        self.join()
        self.update()
        self.polig_table.removeJoin(self.join_object.joinLayerId())
        self.remove_fields()
        QgsMessageLog.logMessage('Procés finalitzat: Poligonal actualitzada', level=Qgis.Info)

    def set_layers(self):
        """ Set the necessary Vector layers """
        self.polig_points_layer = QgsVectorLayer(os.path.join(self.doc_delim, 'Cartografia/Pto_Polig.shp'))
        self.polig_table = QgsVectorLayer(os.path.join(self.doc_delim, 'Taules/POLIGONA.dbf'))

    # #######################
    # Add fields
    def add_fields(self):
        """ Add the necessary fields to both poligonal's layer and table """
        self.add_fields_layer()
        self.add_fields_table()

    def add_fields_layer(self):
        """ Add the necessary fields to the poliognal's point layer """
        concat_field = QgsField(name='Concat_1', type=QVariant.String, typeName='text', len=12)
        x_coord_field = QgsField(name='X_Coord', type=QVariant.Double, len=19, prec=5)
        y_coord_field = QgsField(name='Y_Coord', type=QVariant.Double, len=19, prec=5)

        new_fields_list = (x_coord_field, y_coord_field, concat_field)
        self.polig_points_layer.dataProvider().addAttributes(new_fields_list)
        self.polig_points_layer.updateFields()
        QgsMessageLog.logMessage('Camps de Join afegits a la capa de punts de la Poligonal', level=Qgis.Info)

    def add_fields_table(self):
        """ Add the necessary fields to the poligonal's table """
        concat_field = QgsField(name='Concat_2', type=QVariant.String, typeName='text', len=12)

        self.polig_table.dataProvider().addAttributes([concat_field])
        self.polig_table.updateFields()
        QgsMessageLog.logMessage('Camps de Join afegits a la taula de la Poligonal', level=Qgis.Info)

    # #######################
    # Populate fields
    def populate_fields(self):
        """ Populate the new fields of both poligonal's layer and table """
        self.populate_fields_layer()
        self.populate_fields_table()

    def populate_fields_layer(self):
        """ Populate the new fields of the poligonal's layer """
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

        QgsMessageLog.logMessage('Camps de Join de la capa de punts de la Poligonal correctament emplenats', level=Qgis.Info)

    def populate_fields_table(self):
        """ Populate the new fields of the poligonal's table+ """
        with edit(self.polig_table):
            fields = self.polig_table.fields()
            id_field = fields.indexFromName("Concat_2")
            for feature in self.polig_table.getFeatures():
                concat = f"{feature['ID_POLIG']}_{int(feature['ID_VIS'])}"
                attr = {id_field: concat}
                self.polig_table.dataProvider().changeAttributeValues({feature.id(): attr})

        QgsMessageLog.logMessage('Camps de Join de la taula de la Poligonal correctament emplenats', level=Qgis.Info)

    # #######################
    # Join
    def join(self):
        """ Perform and add a left join to the poligonal's table, adding the poligonal's layer """
        # Join parameters
        self.join_object = QgsVectorLayerJoinInfo()
        self.join_object.setJoinLayerId(self.polig_points_layer.id())
        self.join_object.setJoinFieldName('Concat_1')
        self.join_object.setTargetFieldName('Concat_2')
        self.join_object.setJoinLayer(self.polig_points_layer)
        self.join_object.memoryCache = True

        # Perform join
        self.polig_table.addJoin(self.join_object)

        QgsMessageLog.logMessage('Taula i capa de punts de la Poligonal unides amb un Join', level=Qgis.Info)

    # #######################
    # Update
    def update(self):
        """ Update the poligonal's table with the poligonal's layer values of the reprojected coordinates """
        QgsMessageLog.logMessage('Actualitzant taula de la poligonal...', level=Qgis.Info)
        # Fields parameters
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

        QgsMessageLog.logMessage('Taula de la Poligonal actualitzada', level=Qgis.Info)

    # #######################
    # Remove fields
    def remove_fields(self):
        """ Remove the fields added before to perform the process """
        self.remove_fields_layer()
        self.remove_fields_table()
        QgsMessageLog.logMessage('Camps de Join de la taula i la capa de punts de la Poligonal esborrats', level=Qgis.Info)

    def remove_fields_layer(self):
        """ Remove the fields added to the poligonal's layer """
        fields = self.polig_points_layer.fields()
        delete_fields_list = list((fields.indexFromName("X_Coord"), fields.indexFromName("Y_Coord"), fields.indexFromName("Concat_1")))

        with edit(self.polig_points_layer):
            self.polig_points_layer.dataProvider().deleteAttributes(delete_fields_list)

    def remove_fields_table(self):
        """ Remove the fields added to the poligonal's table """
        fields = self.polig_table.fields()
        delete_field = fields.indexFromName("Concat_2")

        with edit(self.polig_table):
            self.polig_table.dataProvider().deleteAttributes([delete_field])

    # #######################
    # Check
    def check_input_data(self):
        """ Check that exist all the necessary input data into the input directory """
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

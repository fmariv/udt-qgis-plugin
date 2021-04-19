# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where the GeneradorMMC class is defined. The main function
of this class is to run the automation process that exports the geometries
and generates the metadata of a municipal map.
***************************************************************************/
"""
from PyQt5.QtWidgets import QMessageBox


class GeneradorMMC(object):

    def __init__(self, municipi_id, data_alta):
        self.municipi_id = municipi_id
        self.data_alta = data_alta

    def start_process(self):
        """ Main entry point """
        e_box = QMessageBox()
        e_box.setIcon(QMessageBox.Critical)
        e_box.setText("Okale")
        e_box.exec_()


# VALIDATORS
def validate_municipi_id(municipi_id):
    """ Check and validate the Municipi ID input for the Generador MMC class """
    # Validate Municipi ID
    if not municipi_id:
        e_box = QMessageBox()
        e_box.setIcon(QMessageBox.Critical)
        e_box.setText("No s'ha indicat cap ID de municipi")
        e_box.exec_()
        return False
    # TODO comprovar que el municipi està a la carpeta indicada

    return True


def validate_data_alta(new_data_alta):
    """ Check and validate the Data alta input for the Generador MMC class """
    # Validate the input date format is correct
    if len(new_data_alta) != 8:
        e_box = QMessageBox()
        e_box.setIcon(QMessageBox.Critical)
        e_box.setText("La Data Alta no és correcte")
        e_box.exec_()
        return False

    return True
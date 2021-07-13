# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin

In this file is where all the dialogs and the GUI are managed.
***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets


def get_ui_class(ui_file_name):
    """ Get UI Python class from @ui_file_name """
    # Folder that contains UI files
    ui_folder_path = os.path.join(os.path.dirname(__file__), 'ui')
    ui_file_path = os.path.join(ui_folder_path, ui_file_name)

    return uic.loadUiType(ui_file_path)[0]


BASE_FORM_CLASS = get_ui_class('udt_plugin_dialog_base.ui')

GENERADOR_MMC_FORM_CLASS = get_ui_class('generador_registre_mmc.ui')

GENERADOR_MMC_COAST_FORM_CLASS = get_ui_class('generador_registre_mmc_costa.ui')

LINE_MMC_FORM_CLASS = get_ui_class('linia_registre_mmc.ui')

AGREGADOR_MMC_FORM_CLASS = get_ui_class('agregador_registre_mmc.ui')

ELIMINADOR_MMC_FORM_CLASS = get_ui_class('eliminador_registre_mmc.ui')

DECIMETRITZADOR_FORM_CLASS = get_ui_class('decimetritzador_dialog.ui')

PREPARE_LINE_FORM_CLASS = get_ui_class('preparar_linia_dialog.ui')

UPDATE_BM_FORM_CLASS = get_ui_class('update_bm_dialog.ui')


class UDTPluginDialog(QtWidgets.QDialog, BASE_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(UDTPluginDialog, self).__init__(parent)
        self.setupUi(self)


class GeneradorMMCDialog(QtWidgets.QDialog, GENERADOR_MMC_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(GeneradorMMCDialog, self).__init__(parent)
        self.setupUi(self)

        
class GeneradorMMCCoastDialog(QtWidgets.QDialog, GENERADOR_MMC_COAST_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(GeneradorMMCCoastDialog, self).__init__(parent)
        self.setupUi(self)


class LineMMCCDialog(QtWidgets.QDialog, LINE_MMC_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(LineMMCCDialog, self).__init__(parent)
        self.setupUi(self)


class AgregadorMMCDialog(QtWidgets.QDialog, AGREGADOR_MMC_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(AgregadorMMCDialog, self).__init__(parent)
        self.setupUi(self)


class EliminadorMMCDialog(QtWidgets.QDialog, ELIMINADOR_MMC_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(EliminadorMMCDialog, self).__init__(parent)
        self.setupUi(self)


class DecimetritzadorDialog(QtWidgets.QDialog, DECIMETRITZADOR_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(DecimetritzadorDialog, self).__init__(parent)
        self.setupUi(self)


class PrepareLineDialog(QtWidgets.QDialog, PREPARE_LINE_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(PrepareLineDialog, self).__init__(parent)
        self.setupUi(self)


class UpdateBMDialog(QtWidgets.QDialog, UPDATE_BM_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(UpdateBMDialog, self).__init__(parent)
        self.setupUi(self)
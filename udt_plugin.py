# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UDTPlugin
                                 A QGIS plugin

 Plugin que automatitza un conjunt de fluxos de treball necessaris per la
 Unitat de Delimitació Territorial de l'ICGC.
                              -------------------
        begin                : 2021-04-08
        copyright            : (C) 2021 by ICGC
        author               : Fran Martín
        email                : Francisco.Martin@icgc.cat
***************************************************************************/
"""

from datetime import datetime
import os.path
import sys

from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QMenu, QToolButton, QMessageBox
from qgis.core import QgsVectorLayer, QgsVectorFileWriter
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .ui_manager import *
from .actions.generador_mmc import GeneradorMMC, validate_data_alta, validate_municipi_id
from .config import *


class UDTPlugin:
    """QGIS Plugin Implementation."""

    ###########################################################################
    # Plugin initialization

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        # Initialize instance attributes
        self.iface = iface
        self.actions = []
        self.menu = self.tr(u'&UDT Plugin')

        # Initialize other instances
        self.generador_mmc = None

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'UDTPlugin_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Set plugin settings
        self.plugin_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/udt.png'))
        self.generador_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/generador.png'))

        # Set QGIS settings. Stored in the registry (on Windows) or .ini file (on Unix)
        self.qgis_settings = QSettings()
        self.qgis_settings.setIniCodec(sys.getfilesystemencoding())

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('UDTPlugin', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Initialize plugin
        self.init_plugin()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&UDT Plugin'),
                action)
            self.iface.removeToolBarIcon(action)

    def init_plugin(self):
        """ Plugin main initialization function """
        # Set plugin's actions
        self.set_actions()
        # Configure the plugin's GUI
        self.configure_gui()
        # Add the actions to the plugin's menu
        self.add_actions_to_menu()

    def set_actions(self):
        """ Set the plugin actions and add them to the action's list """
        # Default plugin action
        self.action_plugin = self.add_action(icon_path=self.plugin_icon_path,
                                             text='UDT Plugin',
                                             callback=self.show_plugin_dialog,
                                             parent=self.iface.mainWindow())
        # REGISTRE MMC
        # Generador
        self.action_generador_mmc = self.add_action(icon_path=self.generador_icon_path,
                                                    text='Generador MMC',
                                                    callback=self.show_generador_mmc_dialog,
                                                    parent=self.iface.mainWindow())

    def configure_gui(self):
        """ Create the menu and toolbar """
        # Create the menu
        self.plugin_menu = QMenu(self.iface.mainWindow())
        # Create the tool button
        self.tool_button = QToolButton()
        self.tool_button.setMenu(self.plugin_menu)
        self.tool_button.setPopupMode(QToolButton.MenuButtonPopup)
        self.tool_button.setDefaultAction(self.action_plugin)
        # Add the menu to the toolbar and to the plugin's menu
        self.iface.addToolBarWidget(self.tool_button)

    def add_actions_to_menu(self):
        """ Add actions to the plugin menu """
        self.plugin_menu.addAction(self.action_generador_mmc)

    ###########################################################################
    # Functionalities

    def show_plugin_dialog(self):
        """ Show the default plugin dialog """
        self.plugin_dlg = UDTPluginDialog()
        self.plugin_dlg.show()

    # GENERADOR MMC
    def show_generador_mmc_dialog(self):
        """ Show the Generador MMC dialog """
        # Show Generador MMC dialog
        self.generador_dlg = GeneradorMMCDialog()
        self.generador_dlg.show()
        # Configure Generador MMC dialog
        self.configure_generador_mmc_dialog()

    def configure_generador_mmc_dialog(self):
        """ Configure the Generador MMC dialog """
        # SETTINGS
        # Text box validators
        self.generador_dlg.municipiID.setValidator(QIntValidator())   # Set only integer values
        self.generador_dlg.dataAlta.setValidator(QIntValidator())
        self.generador_dlg.editDataAlta.setValidator(QIntValidator())
        # Set current date
        self.generador_dlg.dataAlta.setText(datetime.now().strftime("%Y%m%d"))
        # Edit data alta if necessary
        self.generador_dlg.editDataAltaBtn.clicked.connect(self.edit_generador_data_alta)
        # BUTTONS
        # Initialize process button
        self.generador_dlg.initProcessBtn.clicked.connect(self.init_generador_mmc)
        # Remove temp files
        self.generador_dlg.removeTempBtn.clicked.connect(self.remove_temp_files)

    def init_generador_mmc(self):
        """ Run the Generador MMC main process """
        # Catch muni ID
        self.municipi_id = self.generador_dlg.municipiID.text()
        # Catch Data Alta
        self.data_alta = self.generador_dlg.dataAlta.text()
        # Validate municipi ID
        municipi_id_ok = validate_municipi_id(self.municipi_id)
        # TODO comprovar si el municipi té mar i obrir una altra finestra
        # Create Generador MMC instance
        if municipi_id_ok:
            self.generador_mmc = GeneradorMMC(self.municipi_id, self.data_alta)
            self.generador_mmc.start_process()

    def edit_generador_data_alta(self):
        """ Edit the Generador MMC Data Alta if necessary """
        new_data_alta = self.generador_dlg.editDataAlta.text()
        data_alta_ok = validate_data_alta(new_data_alta)
        if data_alta_ok:
            self.generador_dlg.dataAlta.setText(new_data_alta)

    @staticmethod
    def remove_temp_files(self):
        """ Remove temp files """
        # Sembla ser que hi ha un bug que impedeix esborrar els arxius .shp i .dbf si no es tanca i es torna
        # a obrir la finestra del plugin
        temp_list = os.listdir(GENERADOR_WORK_DIR)
        for temp in temp_list:
            if temp.startswith('MM_Fites') or temp.startswith('MM_Linies') or temp.startswith('MM_Poligons'):
                QgsVectorFileWriter.deleteShapeFile(os.path.join(GENERADOR_WORK_DIR, temp))

        info_box = QMessageBox()
        info_box.setText("Arxius temporals esborrats")
        info_box.exec_()

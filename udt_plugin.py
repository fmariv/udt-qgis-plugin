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

import os.path
import sys
from subprocess import call
import webbrowser

from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QMenu, QToolButton
from qgis.core import Qgis, QgsVectorFileWriter, QgsMessageLog
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

# Initialize Qt resources from file resources.py
from .resources import *

from .ui_manager import *
from .actions.generador_mmc import *
from .actions.line_mmc import *
from .actions.agregador_mmc import *
from .actions.eliminador_mmc import *
from .actions.decimetritzador import *
from .actions.check_mm import *
from .actions.update_bm import *
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
        # Generador MMC
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
        # Icons
        self.plugin_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/udt.png'))
        self.decimetritzador_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/decimetritzador.svg'))
        self.prep_line_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/preparar_linia.svg'))
        self.info_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/info.svg'))
        # Registre MMC
        self.mmc_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/mmc.svg'))
        self.generador_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/generador.svg'))
        self.line_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/line.svg'))
        self.agregador_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/agregador.svg'))
        self.eliminador_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/eliminador.svg'))
        # BM5M
        self.bm5m_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/bm5m.svg'))
        self.bm5m_update_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/bm5m_update.svg'))
        # Analysis
        self.analysis_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/analysis.svg'))
        self.analysis_check_mm_icon_path = os.path.join(os.path.join(os.path.dirname(__file__), 'images/analysis_check_mm.svg'))

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
        # ############
        # REGISTRE MMC
        # Generador
        self.action_generador_mmc = self.add_action(icon_path=self.generador_icon_path,
                                                    text='Generador MMC',
                                                    callback=self.show_generador_mmc_dialog,
                                                    parent=self.iface.mainWindow())
        # Agregador
        self.action_agregador_mmc = self.add_action(icon_path=self.agregador_icon_path,
                                                    text='Agregador MMC',
                                                    callback=self.show_agregador_mmc_dialog,
                                                    parent=self.iface.mainWindow())
        # Eliminador
        self.action_eliminador_mmc = self.add_action(icon_path=self.eliminador_icon_path,
                                                    text='Eliminador MMC',
                                                    callback=self.show_eliminador_mmc_dialog,
                                                    parent=self.iface.mainWindow())
        # Line
        self.action_line_mmc = self.add_action(icon_path=self.line_icon_path,
                                               text='Línia MMC (beta)',
                                               callback=self.show_line_mmc_dialog,
                                               parent=self.iface.mainWindow())

        # ############
        # Decimetritzador
        self.action_decimetritzador = self.add_action(icon_path=self.decimetritzador_icon_path,
                                                      text='Decimetritzador',
                                                      callback=self.show_decimetritzador_dialog,
                                                      parent=self.iface.mainWindow())

        # ############
        # Preparar linia
        self.action_prep_line = self.add_action(icon_path=self.prep_line_icon_path,
                                                text='Preparar línia',
                                                callback=self.show_prep_line_dialog,
                                                parent=self.iface.mainWindow())

        # ############
        # Base Municipal
        self.action_bm5m_update = self.add_action(icon_path=self.bm5m_update_icon_path,
                                                  text='Actualitzar BM-5M',
                                                  callback=self.show_bm5m_update_dialog,
                                                  parent=self.iface.mainWindow())

        # ############
        # Anàlisi
        self.action_check_new_mm = self.add_action(icon_path=self.analysis_check_mm_icon_path,
                                                   text='Obtenir nous MM',
                                                   callback=self.analysis_check_mm,
                                                   parent=self.iface.mainWindow())

        # ############
        # Documentació
        self.action_open_docs = self.add_action(icon_path=self.info_icon_path,
                                         text='Informació i ajuda',
                                         callback=self.open_plugin_docs,
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
        # Main Menu
        self.plugin_menu.addAction(self.action_decimetritzador)
        self.plugin_menu.addAction(self.action_prep_line)
        # Create submenus
        # Analysis
        self.analysis_menu = self.plugin_menu.addMenu(QIcon(self.analysis_icon_path), 'Anàlisi')
        self.analysis_menu.addAction(self.action_check_new_mm)
        # Registre MMC
        self.mmc_menu = self.plugin_menu.addMenu(QIcon(self.mmc_icon_path), 'Registre MMC')
        self.mmc_menu.addAction(self.action_generador_mmc)
        self.mmc_menu.addAction(self.action_agregador_mmc)
        self.mmc_menu.addAction(self.action_eliminador_mmc)
        self.mmc_menu.addAction(self.action_line_mmc)
        # BM5M
        self.bm5m_menu = self.plugin_menu.addMenu(QIcon(self.bm5m_icon_path), 'Base Municipal (beta)')
        self.bm5m_menu.addAction(self.action_bm5m_update)
        # Info
        self.plugin_menu.addAction(self.action_open_docs)

    ###########################################################################
    # Functionalities

    def show_plugin_dialog(self):
        """ Show the default plugin dialog """
        self.plugin_dlg = UDTPluginDialog()
        self.plugin_dlg.show()

    # #################################################
    # REGISTRE MMC
    # #######################
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
        self.generador_dlg.dataAlta.setText(datetime.now().strftime("%Y%m%d%H%M"))
        # Edit data alta if necessary
        self.generador_dlg.editDataAltaBtn.clicked.connect(self.edit_generador_data_alta)
        # BUTTONS #######
        # Generate layers
        self.generador_dlg.initProcessBtn.clicked.connect(lambda: self.init_generador_mmc(generation_file='layers'))
        # Open txt report
        self.generador_dlg.openReportBtn.clicked.connect(self.open_report)
        # Generate metadata table
        self.generador_dlg.generateTableBtn.clicked.connect(lambda: self.init_generador_mmc(generation_file='metadata-table'))
        # Generate metadata file
        self.generador_dlg.generateMetadataBtn.clicked.connect(lambda: self.init_generador_mmc(generation_file='metadata-file'))
        # Remove temp files
        self.generador_dlg.removeTempBtn.clicked.connect(lambda: self.remove_generador_temp_files(True))

    def show_generador_mmc_coast_dialog(self):
        """
        Show the Generador MMC dialog when the municipi has a coast, in order to let the user know it and
        edit the coast txt.
        """
        self.generador_costa_dlg = GeneradorMMCCoastDialog()
        self.generador_costa_dlg.show()
        self.configure_generador_mmc_coast_dialog()

    def configure_generador_mmc_coast_dialog(self):
        """ Configure the Generador MMC Coast dialog """
        # BUTTONS #######
        # Open BT5M txt
        self.generador_costa_dlg.openCoastTxtBtn.clicked.connect(self.open_coast_txt)
        # Start generating process
        self.generador_costa_dlg.pushButton.clicked.connect(self.generate_coast_mmc_layers)

    def init_generador_mmc(self, generation_file=None, constructor=False):
        """
        Run the Generador MMC main process and perform multiple actions.
            - Check the inputs.
            - Check if the municipi has a coast.
            - Return the Generador MMC constructor if necessary.
            - Start a generation process with the Generador MMC class.
        :param generation_file: The type of file to generate. Can be 'layers', 'metadata-table' or 'metadata-file'.
        :constructor: Show if the function has to return the Generador MMC constructor or start a generation process.
        """
        # Get input data
        municipi_id, data_alta = self.get_generador_mmc_input_data()
        # Validate the municipi ID input
        municipi_id_ok = self.validate_municipi_id(municipi_id)

        if municipi_id_ok:
            # ########################
            # CONTROLS
            # Before doing any job, check that the input municipi has a MM in sidm3.mapa_municipal_icc and
            # that all the input data exists and is correct
            # Control that the municipi has a considered MM
            generador_mmc_checker = GeneradorMMCChecker(municipi_id)
            mm_exists = generador_mmc_checker.check_mm_exists()
            if not mm_exists:
                self.show_error_message("El municipi no té Mapa Municipal considerat")
                return
            # Control that the input dir and all the input data exist
            inputs_valid = generador_mmc_checker.validate_inputs()
            if not inputs_valid:
                self.show_warning_message("Revisa les carpetes d'entrada del Mapa Municipal.")
                return

            # Check if the given municipi has a coast line. If it has, open a new dialog.
            if municipi_id in municipis_costa:
                self.show_generador_mmc_coast_dialog()
                return
            # Check if the function is called as a Generador MMC constructor
            # If it is, just return the instance. If not, call some method
            self.generador_mmc = GeneradorMMC(municipi_id, data_alta)
            if constructor:
                return self.generador_mmc

            if generation_file == 'layers':
                generador_mmc_layers = GeneradorMMCLayers(municipi_id, data_alta)
                generador_mmc_layers.generate_mmc_layers()
                self.show_success_message('Capes amb geometria generades. Revisa el log.')
            elif generation_file == 'metadata-table':
                generador_mmc_metadata_table = GeneradorMMCMetadataTable(municipi_id, data_alta)
                generador_mmc_metadata_table.generate_metadata_table()
                self.show_success_message('Taula de metadades generada. Revisa-la.')
            elif generation_file == 'metadata-file':
                generador_mmc_metadata_file = GeneradorMMCMetadata(municipi_id, data_alta)
                generador_mmc_metadata_file.generate_metadata_file()
                self.show_success_message('Metadades generades. Revisa-les.')

    def get_generador_mmc_input_data(self):
        """ Get the input data """
        municipi_id = self.generador_dlg.municipiID.text()
        data_alta = self.generador_dlg.dataAlta.text()

        return municipi_id, data_alta

    def generate_coast_mmc_layers(self):
        """ Directly create a Generador MMC instance and run the layers generating process """
        municipi_id, data_alta = self.get_generador_mmc_input_data()
        generador_mmc = GeneradorMMCLayers(municipi_id, data_alta, True)
        generador_mmc.generate_mmc_layers()

    def open_report(self):
        """ Open the Generador txt report """
        # Create Generador mmc instance if it doesn't exist or is the instance of another municipi
        if (self.generador_mmc is None) or (self.generador_mmc.municipi_id != self.generador_dlg.municipiID.text()):
            self.generador_mmc = self.init_generador_mmc(constructor=True)
        # Open the report if the Generador mmc was correctly instanciated
        if self.generador_mmc is not None:
            self.generador_mmc.open_report()

    @staticmethod
    def open_coast_txt():
        """ Open the coast input txt in order to edit the BT5M fulls where the coast line exists """
        os.startfile(COAST_TXT)

    def edit_generador_data_alta(self):
        """ Edit the Generador MMC Data Alta if necessary """
        new_data_alta = self.generador_dlg.editDataAlta.text()
        data_alta_ok = self.validate_data_alta(new_data_alta)
        if data_alta_ok:
            self.generador_dlg.dataAlta.setText(new_data_alta)

    # #######################
    # Linia MMC
    def show_line_mmc_dialog(self):
        """ Show the Generador MMC dialog """
        # Show Generador MMC dialog
        self.line_dlg = LineMMCCDialog()
        self.line_dlg.show()
        # Configure Generador MMC dialog
        self.configure_line_mmc_dialog()

    def configure_line_mmc_dialog(self):
        """ Configure the Line MMC dialog """
        self.line_dlg.lineID.setValidator(QIntValidator())
        # BUTTONS #######
        # Generate line's data
        self.line_dlg.initProcessBtn.clicked.connect(self.init_line_mmc)

    def init_line_mmc(self):
        """
        Run the Line MMC main process. Extract, manage and export the Municipal data of a boundary line
        """
        # Get the line ID
        line_id = self.line_dlg.lineID.text()
        # Validate the line ID
        line_id_ok = self.validate_line_id(line_id)

        if line_id_ok:
            # Instantiate the LineMMC class
            line_mmc = LineMMC(line_id)
            # Check if the line exists into the database, both in the points and lines layers
            line_id_exists_points, line_id_exists_lines = line_mmc.check_line_exists()
            if not line_id_exists_points and line_id_exists_lines:
                self.show_error_message("La línia no existeix a la capa de fites.")
                return
            elif line_id_exists_points and not line_id_exists_lines:
                self.show_error_message("La línia no existeix a la capa de trams de línia.")
                return
            elif not line_id_exists_points and not line_id_exists_lines:
                self.show_error_message("La línia no existeix ni a la capa de fites ni de trams de línia.")
                return
            # Start generation process
            line_mmc.generate_line_data()
            self.show_success_message('Fet')

    # #######################
    # AGREGADOR MMC
    def show_agregador_mmc_dialog(self):
        """ Show the Agregador MMC dialog """
        # Show Agregador MMC dialog
        self.agregador_dlg = AgregadorMMCDialog()
        self.agregador_dlg.show()
        # Configure Agregador MMC dialog
        self.configure_agregador_mmc_dialog()

    def configure_agregador_mmc_dialog(self):
        """ Configure the Agregador MMC dialog """
        # BUTTONS #######
        self.agregador_dlg.importBtn.clicked.connect(self.init_import_agregador_data)
        self.agregador_dlg.addDataBtn.clicked.connect(lambda: self.init_agregador_mmc('add-data'))
        self.agregador_dlg.exportBtn.clicked.connect(lambda: self.init_agregador_mmc('export-data'))
        self.agregador_dlg.rmTempBtn.clicked.connect(lambda: self.remove_temp_files('agregador'))
        self.agregador_dlg.addLayersCanvasBtn.clicked.connect(lambda: self.init_agregador_mmc('add-layers-canvas'))
        self.agregador_dlg.rmLayersCanvasBtn.clicked.connect(lambda: self.init_agregador_mmc('remove-layers-canvas'))

    def init_agregador_mmc(self, job=None):
        """
        Run the Agregador MMC main process and perform multiple actions.
            - Check the inputs.
            - Add the input data to the last Municipal Map of Catalonia.
            - Export the new Municipal Map of Catalonia.
            - Add the working layers to the QGIS canvas.
            - Remove the working layers from the QGIS canvas.
        :param job: The Agregador's class method to call. Can be 'add-data', 'export-data', 'add-layers-canvas' or
                    'remove-layers-canvas'.
        """
        # Check that exists all the necessary data in the workspace
        input_data_ok = check_agregador_input_data()
        if not input_data_ok:
            return
        agregador_mmc = AgregadorMMC()
        # en funcion del job hacer una cosa u otra
        if job == 'add-data':
            agregador_mmc.add_municipal_map_data()
            self.show_success_message('Mapes agregats i duplicats esborrats')
        elif job == 'export-data':
            agregador_mmc.export_municipal_map_data()
            self.show_success_message('Mapa Municipal de Catalunya exportat')
        elif job == 'add-layers-canvas':
            agregador_mmc.add_layers_canvas()
            self.show_success_message('Capes afegides al mapa')
        elif job == 'remove-layers-canvas':
            agregador_mmc.remove_layers_canvas()
            self.show_success_message('Capes esborrades del mapa')

    def init_import_agregador_data(self):
        """ Import the working data from the last Municipal Map of Catalonia """
        input_directory = self.agregador_dlg.dataDirectoryBrowser.filePath()
        input_directory_ok = self.validate_input_directory(input_directory)

        if input_directory_ok:
            import_agregador_data(input_directory)
            self.show_success_message('Dades del MMC importades correctament')

    # #######################
    # ELIMINADOR MMC
    def show_eliminador_mmc_dialog(self):
        """ Show the Eliminador MMC dialog """
        # Show Generador MMC dialog
        self.eliminador_dlg = EliminadorMMCDialog()
        self.eliminador_dlg.show()
        # Configure Generador MMC dialog
        self.configure_eliminador_mmc_dialog()

    def configure_eliminador_mmc_dialog(self):
        """ Configure the Eliminador MMC dialog """
        self.eliminador_dlg.municipiID.setValidator(QIntValidator())
        # BUTTONS #######
        self.eliminador_dlg.rmDataBtn.clicked.connect(self.init_eliminador_mmc)
        self.eliminador_dlg.rmTempBtn.clicked.connect(lambda: self.remove_temp_files('eliminador'))

    def init_eliminador_mmc(self):
        """ Run the Eliminador MMC process """
        # Get input data
        municipi_id = self.eliminador_dlg.municipiID.text()
        # Validate the municipi ID input
        municipi_id_ok = self.validate_municipi_id(municipi_id)

        if municipi_id_ok:
            # Check that exists the input Municipal Map of Catalonia and all the necessary layers
            input_data_ok = check_eliminador_input_data()
            if input_data_ok:
                if municipi_id in municipis_costa:
                    eliminador_mmc = EliminadorMMC(municipi_id, True)
                else:
                    eliminador_mmc = EliminadorMMC(municipi_id)
                # Check that the municipi to remove exists in the input Municipal Map of Catalonia
                municipi_ine = eliminador_mmc.get_municipi_codi_ine(int(municipi_id))
                municipi_exists = eliminador_mmc.check_mm_exists(municipi_ine)
                if municipi_exists:
                    eliminador_mmc.remove_municipi_data()
                    self.show_success_message('Mapa municipal esborrat.')
                else:
                    self.show_error_message('El municipi introduit no té mapa municipal considerat.')

    # #################################################
    # Decimetritzador
    def show_decimetritzador_dialog(self):
        """ Show the Decimetritzador dialog """
        # Show Decimetritzador dialog
        self.decimetritzador_dlg = DecimetritzadorDialog()
        self.decimetritzador_dlg.show()
        # Configure Generador MMC dialog
        self.configure_decimetritzador_dialog()

    def configure_decimetritzador_dialog(self):
        """ Configure the Decimetritzador dialog """
        self.decimetritzador_dlg.initProcessBtn.clicked.connect(self.init_decimetritzador)

    def init_decimetritzador(self):
        """ Run the Decimetritzador process """
        input_directory = self.decimetritzador_dlg.decimetritzadorDirectoryBrowser.filePath()
        input_directory_ok = self.validate_input_directory(input_directory)

        if input_directory_ok:
            decimetritzador = Decimetritzador(input_directory)
            decimetritzador_data_ok = decimetritzador.check_input_data()
            if decimetritzador_data_ok:
                decimetritzador.decimetritzar()
                self.show_success_message('Capes decimetritzades')

    # #################################################
    # Preparar línia
    def show_prep_line_dialog(self):
        """ Show the Prepare Line dialog """
        # Show Generador MMC dialog
        self.prep_line_dlg = PrepareLineDialog()
        self.prep_line_dlg.show()
        # Configure Generador MMC dialog
        self.configure_prep_line_dialog()

    def configure_prep_line_dialog(self):
        """ Configure the Prepare Line dialog """
        self.prep_line_dlg.lineID.setValidator(QIntValidator())
        # BUTTONS #######
        self.prep_line_dlg.initProcessBtn.clicked.connect(self.prepare_line)

    def prepare_line(self):
        """
        Run the prepare line bat file, which launch a process that extracts a line's data from the UDT unit's
        NAS in order to create a folder with all the necessary data for boundary delimitation
        """
        # Get line ID
        line_id = self.prep_line_dlg.lineID.text()
        # Check line ID
        line_id_ok = self.validate_line_id(line_id)

        if line_id_ok:
            script_dir = os.path.join(self.plugin_dir, 'scripts/prep_linia')
            script = os.path.join(script_dir, 'prep_linia.bat')
            call([script, line_id, script_dir])

    # #################################################
    # Base municipal
    # #######################
    # Actualitzar Base municipal
    def show_bm5m_update_dialog(self):
        """ Show the BM-5M update dialog """
        self.update_bm_dlg = UpdateBMDialog()
        self.update_bm_dlg.show()
        self.configure_bm5m_update_dialog()

    def configure_bm5m_update_dialog(self):
        """ Configure the BM-5M update dialog """
        self.update_bm_dlg.initProcessBtn.clicked.connect(self.init_bm5m_update)

    def init_bm5m_update(self):
        """  """
        date_last_update = self.update_bm_dlg.lastUpdateDate.text()
        date_last_update_ok = self.validate_date_last_update(date_last_update)

        if date_last_update_ok:
            bm_updater = UpdateBM(date_last_update)
            bm_data_ok = bm_updater.check_bm_data()
            if bm_data_ok:
                bm_updater.update_bm()

    # #################################################
    # Anàlisi
    # #######################
    # Check new MM
    def analysis_check_mm(self):
        """ Perform an analysis that checks if there are any municipis ready to generate them Municipal Map """
        check_mm = CheckMM()
        check_mm.get_new_mm()
        self.show_success_message('Anàlisi de nous MM realitzat. Si us plau, ves al report per veure els resultats.')

    # #################################################
    # Documentació
    @staticmethod
    def open_plugin_docs():
        """ Go to the plugin documentation """
        webbrowser.open(DOCS_PLUGIN_URL)

    # #################################################
    # QGIS Messages
    def show_success_message(self, text):
        """ Show a QGIS success message """
        self.iface.messageBar().pushMessage('OK', text, level=Qgis.Success)

    def show_error_message(self, text):
        """ Show a QGIS error message """
        self.iface.messageBar().pushMessage('Error', text, level=Qgis.Critical)

    def show_warning_message(self, text):
        """ Show a QGIS warning message """
        self.iface.messageBar().pushMessage('Atenció', text, level=Qgis.Warning)

    # #################################################
    # Validators
    def validate_municipi_id(self, municipi_id):
        """ Check and validate the Municipi ID input for the Generador MMC class """
        # Validate Municipi ID
        if not municipi_id:
            self.show_error_message("No s'ha indicat cap ID de municipi")
            return False

        return True

    def validate_data_alta(self, new_data_alta):
        """ Check and validate the Data alta input for the Generador MMC class """
        # Validate the input date format is correct
        if len(new_data_alta) != 8:
            self.show_error_message("La Data d'alta no és correcte")
            return False

        return True

    def validate_date_last_update(self, date_last_update):
        """   """
        if not date_last_update:
            self.show_error_message("No s'ha indicat cap data de l'última actualització")
            return False

        if not date_last_update.isdecimal() or len(date_last_update) != 12:
            self.show_error_message("La data de l'última actualització introduïda no és correcte")
            return False

        return True

    def validate_line_id(self, line_id):
        """ Check and validate the line ID input for the Line MMC class """
        # Validate line ID
        if not line_id:
            self.show_error_message("No s'ha indicat cap ID de línia")
            return False

        return True

    def validate_input_directory(self, directory):
        """ Check if the user has selected and input directory """
        if not directory:
            self.show_error_message("No s'ha seleccionat cap directori")
            return False

        return True

    # #################################################
    # Remove temporal files
    def remove_generador_temp_files(self, message=False):
        """ Remove the Generador MMC's temporal files """
        # Sembla ser que hi ha un bug que impedeix esborrar els arxius .shp i .dbf si no es tanca i es torna
        # a obrir la finestra del plugin
        temp_list = os.listdir(GENERADOR_WORK_DIR)
        for temp in temp_list:
            if temp in TEMP_ENTITIES:
                try:
                    QgsVectorFileWriter.deleteShapeFile(os.path.join(GENERADOR_WORK_DIR, temp))
                except Exception as error:
                    self.show_error_message("No s'han pogut esborrar els arxius temporals.")
                    QgsMessageLog.logMessage(error)
                    return

        if message:
            self.show_success_message('Arxius temporals esborrats.')

    def remove_temp_files(self, action):
        """ Remove temporal files from the working directory of the given action """
        directory = ''
        if action == 'agregador':
            directory = AGREGADOR_WORK_DIR
        elif action == 'eliminador':
            directory = ELIMINADOR_WORK_DIR
        temp_files_list = os.listdir(directory)
        if len(temp_files_list) == 0:
            self.show_warning_message('No existeixen arxius temporals a esborrar')
            return
        for file in temp_files_list:
            try:
                file_path = os.path.join(directory, file)
                os.remove(file_path)
            except Exception as error:
                self.show_error_message("No s'han pogut esborrar els arxius temporals.")
                return

        self.show_success_message('Arxius temporals esborrats')

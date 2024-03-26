# coding=utf-8
from __future__ import absolute_import, unicode_literals
from concurrent.futures import ThreadPoolExecutor

import re
import io
import os
import sys

import octoprint.plugin
import octoprint.events
import octoprint.filemanager
import octoprint.filemanager.storage
import octoprint.filemanager.util
from octoprint.events import Events

from .const import *
from .metadata import *
from .util import *
from octoprint_SlicerEstimator.estimator import SlicerEstimator, SlicerEstimatorGcodeAnalysisQueue
from flask_babel import gettext

class SlicerEstimatorPlugin(octoprint.plugin.StartupPlugin,
                            octoprint.plugin.TemplatePlugin,
                            octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.EventHandlerPlugin,
                            octoprint.plugin.SimpleApiPlugin,
                            octoprint.plugin.ProgressPlugin,
                            octoprint.plugin.AssetPlugin,
                            octoprint.plugin.ReloadNeedingPlugin,
                            octoprint.filemanager.util.LineProcessorStream):
    def __init__(self):
        self._estimator = None
        self._slicer_estimation = None
        self._executor = ThreadPoolExecutor()
        self._plugins = dict()
        self._filedata = dict()
        self._slicer_filament_change = None
        self._filament_change_cnt = 0



# SECTION: Settings
    def on_after_startup(self):
        self._logger.info("Started up SlicerEstimator")
        # Setting löschen: self._settings.set([], None)
        self._update_settings_from_config()
        self._cleanup_uninstalled_plugins()

        # self.on_settings_migrate(3,1)
        # Example for API calls
        # helpers = self._plugin_manager.get_helpers("SlicerEstimator",
        #                                            "register_plugin",
        #                                            "register_plugin_target",
        #                                            "unregister_plugin",
        #                                            "unregister_plugin_target",
        #                                            "get_metadata_file"
        #                                            )
        # if helpers is None:
        #     self._logger.info("Slicer Estimator not installed")
        # else:
        #     self.se_register_plugin = helpers["register_plugin"]
        #     self.se_register_plugin_target = helpers["register_plugin_target"]
        #     self.se_unregister_plugin = helpers["unregister_plugin"]
        #     self.se_unregister_plugin_target = helpers["unregister_plugin_target"]
        #     self.se_get_metadata_file = helpers["get_metadata_file"]

        #     self.se_register_plugin(self._identifier, self._plugin_name)
        #     self.se_register_plugin_target(self._identifier, "filelist_mobile_id","Filelist in Mobile")
        #     metadata = self.se_get_metadata_file(self._identifier,"filelist_mobile_id", "local", "Wanderstöcke Halterung.gcode")


    def get_settings_defaults(self):
        plugins = dict()
        plugins[self._identifier] = dict()
        plugins[self._identifier]["name"] = self._plugin_name,
        plugins[self._identifier]["targets"] = dict(printer= "Printer", filelist= "Filelist")

        return dict(
            average_prio=True,
            use_assets=True,
            metadata_filelist=True,
            metadata_filelist_align="top",
            metadata_printer=True,
            metadata_list=[],
            metadata_slicer=True,
            useDevChannel=False,
            plugins=plugins
            )


    def get_settings_version(self):
        return 3


    def on_settings_migrate(self, target, current):
        self._logger.info("SlicerEstimator: Updating Metadata from files...")
        metadata_handler = SlicerEstimatorMetadataFiles(self)
        metadata_handler.update_metadata_in_files()

        if current is not None:
            self._logger.info("SlicerEstimator: Setting migration from version {} to {}".format(current, target))

            if current < 2:
                # Move settings to a dynamic dict to support other plugins
                metadata_list = self._settings.get(["metadata_list"])
                for meta_items in metadata_list:
                    meta_items["targets"] = dict()
                    meta_items["targets"][self._identifier] = dict()
                    meta_items["targets"][self._identifier]["printer"] = meta_items["printer"]
                    meta_items["targets"][self._identifier]["filelist"] = meta_items["filelist"]
                    del meta_items["printer"]
                    del meta_items["filelist"]
                self._settings.set(["metadata_list"], metadata_list)
                plugins = dict()
                plugins[self._identifier] = dict()
                plugins[self._identifier]["name"] = self._plugin_name,
                plugins[self._identifier]["targets"] = dict(printer= "Printer", filelist= "Filelist")
                self._settings.set(["plugins"], plugins)


    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._update_settings_from_config()


    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]



# SECTION: Settings helper
    def _update_settings_from_config(self):
        self._average_prio = self._settings.get(["average_prio"])
        self._metadata_list = self._settings.get(["metadata_list"])
        self._useDevChannel = self._settings.get(["useDevChannel"])
        self._plugins = self._settings.get(["plugins"])
        self._metadata_slicer = self._settings.get(["metadata_slicer"])

        if self._estimator != None:
            self._estimator.average_prio = self._average_prio

        self._logger.debug("Average: {}".format(self._average_prio))


    # sends the data-dictonary to the client/browser
    def _sendDataToClient(self, dataDict):
        self._plugin_manager.send_plugin_message(self._identifier, dataDict)


    #send notification to client/browser
    def _sendNotificationToClient(self, notifyMessageID):
        self._logger.debug("Plugin message: {}".format(notifyMessageID))
        self._plugin_manager.send_plugin_message(self._identifier, dict(notifyMessageID=notifyMessageID))



# SECTION: Estimation
    # Called by at sign in GCODE
    def on_at_command(self, comm, phase, command, parameters, tags=None, *args, **kwargs):
        if phase == "sending" and command == "TIME_LEFT" and isinstance(self._estimator, SlicerEstimator):            
            self._estimator.time_left = float(parameters)


    # Process Gcode
    def on_gcode_sent(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        # Update Filament Change Time and Position from actual print        
        if self._slicer_filament_change and (gcode == "M600" or gcode =="T") and isinstance(self._estimator, SlicerEstimator):
            if self._estimator.time_left > -1.0:
                self._slicer_filament_change[self._filament_change_cnt][1] = self._estimator.time_left
            self._slicer_filament_change[self._filament_change_cnt][3] = comm_instance._currentFile._pos
            self._filament_change_cnt += 1


    # Hook after file upload for pre-processing
    def on_file_upload(self, path, file_object, links=None, printer_profile=None, allow_overwrite=True, *args, **kwargs):
        cleaned_path = str(path).lstrip("/")        
        if not octoprint.filemanager.valid_file_type(path, type="gcode"):
            return file_object
        filedata = SlicerEstimatorFiledata(path, file_object, self)
        self._filedata[cleaned_path] = filedata
        return octoprint.filemanager.util.StreamWrapper(file_object.filename, filedata)


    # EventHandlerPlugin for native information search
    def on_event(self, event, payload):
        self._logger.debug("Event received: {}".format(event))
        self._logger.debug("Payload: {}".format(payload))
        if event == Events.PRINT_STARTED:
            origin = payload["origin"]
            path = payload["path"]
            if origin == "local":
                self._filament_change_cnt = 0
                slicer_additional = self._file_manager._storage_managers["local"].get_additional_metadata(path,"slicer_additional")
                if slicer_additional:
                    if isinstance(self._estimator, SlicerEstimator):
                        if slicer_additional["slicer"] == SLICER_SIMPLIFY3D:
                            # Simplify3D has no embedded time left
                            self._estimator.use_progress = True
                            self._estimator.time_total = slicer_additional["printtime"]
                        else:
                            self._estimator.use_progress = False
                            self._estimator.time_total = slicer_additional["printtime"]
                            self._estimator.time_left = slicer_additional["printtime"]
                else:
                    #TODO: Start rebuilding metadata automatically
                    self._sendNotificationToClient("no_estimation")
                self._slicer_filament_change = self._file_manager._storage_managers["local"].get_additional_metadata(path,"slicer_filament_change")
                self._send_metadata_print_event(origin, path)
                self._send_filament_change_event(origin, path)

        if event == Events.PRINT_CANCELLED or event == Events.PRINT_FAILED or event == Events.PRINT_DONE:
            # Init of Class variables for new estimation
            self._slicer_estimation = None
            self._sliver_estimation_str = None
            if isinstance(self._estimator, SlicerEstimator):
                self._estimator.time_left = -1.0
                self._estimator.time_total = -1.0
                self._estimator.use_progress = False
            self._slicer_filament_change = None

        if event == Events.PRINT_DONE:
            origin = payload["origin"]
            path = payload["path"]
            self._file_manager._storage_managers["local"].set_additional_metadata(path, "slicer_filament_change", self._slicer_filament_change, overwrite=True)

        if event == Events.FILE_ADDED:
            if payload["storage"] == "local" and payload["type"][1] == "gcode":
                self._logger.debug("Filedata of {}: {}".format(payload["path"], vars(self._filedata[payload["path"]])))
                if self._filedata[payload["path"]].slicer == None:
                    self._sendNotificationToClient("no_slicer_detected")
                self._filedata[payload["path"]].store_metadata()


    # estimator factory hook
    def estimator_factory(self):
        def factory(*args, **kwargs):
            self._estimator = SlicerEstimator(*args, **kwargs)
            self._estimator.average_prio = self._average_prio
            return self._estimator
        return factory



# SECTION: Analysis Queue Estimation (file upload)
    def analysis_queue_factory(self, *args, **kwargs):
        return dict(gcode=lambda finished_callback: SlicerEstimatorGcodeAnalysisQueue(finished_callback, self))


    def run_analysis(self, path):
        slicer_additional = self._file_manager._storage_managers["local"].get_additional_metadata(self.path,"slicer_additional")
        if slicer_additional:
                self._estimator.estimated_time = slicer_additional["printtime"]
        else:
            self._logger.warning("Slicer-Estimation not found. Please check if you selected the correct slicer.")



# SECTION: API
    def register_plugin(self, plugin_identifier, plugin_name):
        """Register a plugin to add it to the setting

        Args:
            plugin_identifier (String): OctoPrint Plugin Identifier
            plugin_name (String): OctoPrints plugins name (or any other name you like to use)
        """
        if plugin_identifier in self._plugin_manager.plugins.keys():
            if plugin_identifier in self._plugins:
                self._logger.debug("Plugin {} already registered".format(plugin_identifier))
            else:
                self._logger.debug("Plugin {} registered".format(plugin_identifier))
                self._plugins[plugin_identifier] = dict()
                self._plugins[plugin_identifier]["name"] = plugin_name
                self._plugins[plugin_identifier]["targets"] = dict()
                self._settings.set(["plugins"], self._plugins)
        else:
            self._logger.error("Plugin {} tried to register but not found in OctoPrint's Plugin Manager".format(plugin_identifier))


    def register_plugin_target(self, plugin_identifier, target, target_name):
        """Register a target to an existing plugin - call multiple time for new targets

        Args:
            plugin_identifier (String): OctoPrint Plugin Identifier
            target (String): ID of a target (you can choose)
            target_name (String): Name of a target to use in the dropdown
        """
        if plugin_identifier in self._plugins:
            if target in self._plugins[plugin_identifier]["targets"].keys():
                self._logger.debug("Plugins {} target {} already registered".format(plugin_identifier, target))
            else:
                self._plugins[plugin_identifier]["targets"][target] = target_name
                self._settings.set(["plugins"], self._plugins)
                for meta_items in self._metadata_list:
                    meta_items["targets"][plugin_identifier] = dict()
                    meta_items["targets"][plugin_identifier][target] = False
                    self._settings.set(["metadata_list"], self._metadata_list)
                self._logger.debug("Plugins {} target {} registered".format(plugin_identifier, target))
        else:
            self._logger.error("Plugin {} tried to register target {} but not found in registry".format(plugin_identifier, target))


    def unregister_plugin(self, plugin_identifier):
        """Unrgister a plugin if you like to remove all settings

        Args:
            plugin_identifier (String): OctoPrint Plugin Identifier
        """
        if self._plugins[plugin_identifier].pop() is None:
            self._logger.info("Plugin {} not found to unregister".format(plugin_identifier))
        else:
            for meta_items in self._metadata_list:
                meta_items["targets"][plugin_identifier].pop()
                self._settings.set(["metadata_list"], self._metadata_list)
            self._logger.info("Plugin {} unregistered".format(plugin_identifier))


    def unregister_plugin_target(self, plugin_identifier, target):
        """Unrgister a plugins target if you like to remove all target settings

        Args:
            plugin_identifier (String): OctoPrint Plugin Identifier
            target (String): ID of a target (you can choose)
        """
        if plugin_identifier in self._plugins:
            for meta_items in self._metadata_list:
                if meta_items["targets"][plugin_identifier][target].pop() is None:
                    self._logger.error("Could not unregister plugins {} target {}!".format(plugin_identifier, target))
                self._settings.set(["metadata_list"], self._metadata_list)
            self._logger.info("Plugin {} unregistered target {}".format())
        else:
            self._logger.error("Plugin {} tried to unregister target {} but not found in registry".format(plugin_identifier, target))


    def get_registered_plugins(self):
        """Return list of plugins registered

        Returns:
            array of strings: List of plugin identifiers registered
        """
        return self._plugins.keys()


    def get_registered_plugin_targets(self, plugin_identifier):
        """Returns list of targets registered for a plugin

        Args:
            plugin_identifier (String): plugin_identifier to check

        Returns:
            array of strings: List of targets registered for a plugin
        """
        if plugin_identifier in self._plugins.keys():
            return self._plugins[plugin_identifier]["targets"].keys()
        else:
            self._logger.error("Plugin {} tried to gets targets but not found in registry".format(plugin_identifier))


    def get_metadata_file(self, plugin_identifier, target, origin, path):
        """Get the Metadata to a file in an Array containing a tripple array

        Args:
            plugin_identifier (String): OctoPrint Plugin Identifier
            target (String): ID of a target (you can choose)
            origin (String): only "local" supported actually
            path (String): Path to the file

        Returns:
            [Array]: Array of metadata in metadata_id, description and value
        """
        if origin != "local":
            self._logger.error("Only local origin supported!")
        if plugin_identifier in self._plugins:
            if target in self._plugins[plugin_identifier]["targets"].keys():
                return_list = []
                meta_selected = filter(lambda elem: elem["targets"][plugin_identifier][target] == True, self._metadata_list)
                additional_metadata = self._file_manager._storage_managers[origin].get_additional_metadata(path, "slicer_metadata")
                if additional_metadata:
                    for meta_item in meta_selected:
                        if meta_item["id"] in additional_metadata:
                            return_item = [meta_item["id"], meta_item["description"], additional_metadata[meta_item["id"]]]
                            return_list.append(return_item)
                return return_list
            else:
                self._logger.error("Target {} of plugin {} not registered.".format(target, plugin_identifier))
        else:
            self._logger.error("Plugin {} not registered.".format(plugin_identifier))


    # send the event on printing
    def _send_metadata_print_event(self, origin, path):
        event = "plugin_SlicerEstimator_metadata_print"
        custom_payload = dict()
        for plugin in self._plugins:
            custom_payload[plugin] = dict()
            for target in self._plugins[plugin]["targets"]:
                custom_payload[plugin][target] = self.get_metadata_file(plugin, target, origin, path)
        self._logger.info("Send Metadata Print Event for file {}".format(path))
        self._event_bus.fire(event, payload=custom_payload)


    def _send_filament_change_event(self, origin, path):
        event = "plugin_SlicerEstimator_filament_change"
        custom_payload = self._file_manager._storage_managers[origin].get_additional_metadata(path,"slicer_filament_change")
        if custom_payload:
            self._logger.info("Send Filament Change Event for file {}".format(path))
            self._event_bus.fire(event, payload=custom_payload)


    # Cleanup uninstalled registered plugins
    def _cleanup_uninstalled_plugins(self):
        for plugin in self._plugins.keys():
            if plugin not in self._plugin_manager.plugins.keys():
                self.unregister_plugin(plugin)


    def get_api_commands(self):
        return {'deleteMetadataStored': [], 'updateMetadataStored': []}

    def on_api_command(self, command, data):
        import flask
        from octoprint.server import user_permission
        if not user_permission.can():
            return flask.make_response("Insufficient rights", 403)

        if command == "deleteMetadataStored":
            self._logger.debug("Deleting metadata stored")
            metadataFileObj = SlicerEstimatorMetadataFiles(self)
            metadataFileObj.delete_metadata_in_files()
            # return flask.jsonify(results)
        elif command == "updateMetadataStored":
            self._logger.debug("Updating metadata stored")
            metadataFileObj = SlicerEstimatorMetadataFiles(self)
            metadataFileObj.update_metadata_in_files()
            # return flask.jsonify(results)




# SECTION: Assets
    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        self._logger.debug("Assets registered")
        return dict(
            js=["js/SlicerEstimator.js"],
            css=["css/SlicerEstimator.css"],
            less=["less/SlicerEstimator.less"]
        )



# SECTION: software update hook
    def get_update_information(self):
        if hasattr(self, "_settings"):
            DevChannel = self._settings.get_boolean(["useDevChannel"])
        else:
            DevChannel = False

        if DevChannel:
            return dict(
                SlicerEstimator=dict(
                    displayName=self._plugin_name + " (Development Branch)",
                    displayVersion=self._plugin_version,

                    # version check: github repository
                    type="github_commit",
                    user="NilsRo",
                    repo="OctoPrint-SlicerEstimator",
                    branch="Development",

                    # update method: pip
                    # pip="https://github.com/NilsRo/OctoPrint-SlicerEstimator/archive/{target_version}.zip"
                    method="update_script",
                    update_script="{python} -m pip --disable-pip-version-check install https://github.com/NilsRo/OctoPrint-SlicerEstimator/archive/refs/heads/Development.zip --force-reinstall --no-deps --no-cache-dir",
                    checkout_folder = os.path.dirname(os.path.realpath(sys.executable)),
                    restart = "octoprint"
                )
            )
        else:
            return dict(
                SlicerEstimator=dict(
                    displayName=self._plugin_name,
                    displayVersion=self._plugin_version,

                    # version check: github repository
                    type="github_release",
                    user="NilsRo",
                    repo="OctoPrint-SlicerEstimator",
                    current=self._plugin_version,

                    # stable release
                    stable_branch=dict(
                        name="Stable",
                        branch="master",
                        comittish=["master"]
                    ),

                    # update method: pip
                    pip="https://github.com/NilsRo/OctoPrint-SlicerEstimator/archive/{target_version}.zip"
                )
        )





__plugin_name__ = "Slicer Estimator"
__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def _register_custom_events(*args, **kwargs):
    return ["metadata_print"]



# SECTION: Register API for other plugins
def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SlicerEstimatorPlugin()

    global __plugin_helpers__
    __plugin_helpers__ = dict(
        register_plugin=__plugin_implementation__.register_plugin,
        register_plugin_target = __plugin_implementation__.register_plugin_target,
        unregister_plugin=__plugin_implementation__.unregister_plugin,
        unregister_plugin_target=__plugin_implementation__.unregister_plugin_target,
        get_metadata_file=__plugin_implementation__.get_metadata_file
    )

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.on_gcode_sent,
        "octoprint.printer.estimation.factory": __plugin_implementation__.estimator_factory,
        "octoprint.filemanager.analysis.factory": __plugin_implementation__.analysis_queue_factory,
        "octoprint.filemanager.preprocessor": __plugin_implementation__.on_file_upload,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.atcommand.sending": __plugin_implementation__.on_at_command,
        "octoprint.events.register_custom_events": _register_custom_events
    }
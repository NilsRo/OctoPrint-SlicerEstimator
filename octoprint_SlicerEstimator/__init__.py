# coding=utf-8
from __future__ import absolute_import, unicode_literals
from concurrent.futures import ThreadPoolExecutor
from octoprint.printer.estimation import PrintTimeEstimator

import octoprint.plugin
import octoprint.events
import octoprint.filemanager.storage
import re
import io
import time
import os
import sys
import collections


from octoprint.filemanager.analysis import AnalysisAborted
from octoprint.filemanager.analysis import GcodeAnalysisQueue
from octoprint.printer.estimation import PrintTimeEstimator
from octoprint.events import Events

class SlicerEstimator(PrintTimeEstimator):
    def __init__(self, job_type):
        PrintTimeEstimator.__init__(self, job_type)
        self._job_type = job_type
        self.estimated_time = -1
        self.average_prio = False


    def estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
        std_estimator = PrintTimeEstimator.estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType)

        if self._job_type != "local" or self.estimated_time == -1:
            # using standard estimator
            return std_estimator
        elif std_estimator[1] == "average" and self.average_prio:
            # average more important than estimation
            return std_estimator
        else:
            # return "slicerestimator" as Origin of estimation
            return self.estimated_time, "slicerestimator"


class SlicerEstimatorPlugin(octoprint.plugin.StartupPlugin,
                            octoprint.plugin.TemplatePlugin,
                            octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.EventHandlerPlugin,
                            octoprint.plugin.ProgressPlugin,
                            octoprint.plugin.AssetPlugin,
                            octoprint.plugin.ReloadNeedingPlugin):
    def __init__(self):
        self._estimator = None
        self._slicer_estimation = None
        self._executor = ThreadPoolExecutor()
        self._plugins = dict()

        # Slicer defaults - actual Cura M117, PrusaSlicer, Cura, Simplify3D
        self._slicer_def = [
                ["M117","","",
                "M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
                "M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
                "M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
                1,1,1,2,3,"GCODE","M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s"],
                ["M73","","",
                "",
                "M73 P([0-9]+) R([0-9]+).*",
                "",
                1,1,1,2,1,"GCODE","M73 P([0-9]+) R([0-9]+).*"],
                ["","","",
                "",
                "",
                ";TIME:([0-9]+)",
                1,1,1,1,1,"COMMENT",";TIME:([0-9]+)"],
                ["","","",
                ";   Build time: ([0-9]+) hours? ([0-9]+) minutes",
                ";   Build time: ([0-9]+) hours? ([0-9]+) minutes",
                "",
                1,1,1,2,1,"COMMENT",";   Build time: ([0-9]+) hours? ([0-9]+) minutes"]]


# SECTION: Settings
    def on_after_startup(self):
        self._logger.info("Started up SlicerEstimator")
        # Setting löschen: self._settings.set([], None)
        self._update_settings_from_config()
        # TODO ausbauen
        self._update_metadata_in_files()

        # Example for API calls
        # helpers = self._plugin_manager.get_helpers("SlicerEstimator", 
        #                                            "register_plugin", 
        #                                            "register_plugin_target",
        #                                            "unregister_plugin",
        #                                            "unregister_plugin_target",
        #                                            "get_metadata_api"
        #                                            )
        # if helpers is None:
        #     self._logger.info("Slicer Estimator not installed")
        # else:            
        #     self.se_register_plugin = helpers["register_plugin"]
        #     self.se_register_plugin = helpers["register_plugin_target"]
        #     self.se_register_plugin = helpers["unregister_plugin"]
        #     self.se_register_plugin = helpers["unregister_plugin_target"]
        #     self.se_register_plugin = helpers["get_metadata_api"]
            
        #     self.se_register_plugin(self._identifier, self._plugin_name)
        #     self.se_register_plugin_target(self._identifier, "filelist_mobile_id","Filelist in Mobile")
        #     metadata = self.get_metadata_file(self._identifier,"Blupp_target", "local", "Wanderstöcke Halterung.gcode")


    def get_settings_defaults(self):
        plugins = dict()
        plugins[self._identifier] = dict()
        plugins[self._identifier]["name"] = self._plugin_name,
        plugins[self._identifier]["targets"] = dict(printer= "Printer", filelist= "Filelist")

        return dict(
            slicer="2",
            slicer_gcode="M117",
            pw="",
            pd="",
            ph="M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
            pm="M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
            ps="M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
            pwp=1,
            pdp=1,
            php=1,
            pmp=2,
            psp=3,
            search_mode="GCODE",
            search_pattern="",
            average_prio=False,
            use_assets=True,
            slicer_auto=True,
            estimate_upload=True,
            metadata=False,
            metadata_filelist=True,
            metadata_filelist_align="top",
            metadata_printer=False,
            metadata_list=[],
            useDevChannel=False,
            plugins=plugins
            )


    def get_settings_version(self):
        return 2


    def on_settings_migrate(self, target, current):
        if current is not None:
            self._logger.info("SlicerEstimator: Setting migration from version {} to {}".format(current, target))
            self._update_metadata_in_files()

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
        self._slicer_conf = self._settings.get(["slicer"])
        self._logger.debug("SlicerEstimator: Slicer Setting {}".format(self._slicer_conf))

        self._slicer_auto = self._settings.get(["slicer_auto"])
        self._average_prio = self._settings.get(["average_prio"])
        self.estimate_upload = self._settings.get(["estimate_upload"])
        self._metadata = self._settings.get(["metadata"])
        self._metadata_list = self._settings.get(["metadata_list"])
        self._useDevChannel = self._settings.get(["useDevChannel"])
        self._plugins = self._settings.get(["plugins"])

        if self._estimator != None:
            self._estimator.average_prio = self._average_prio

        self._logger.debug("Average: {}".format(self._average_prio))

        if self._slicer_conf == "c":
            self._slicer = self._slicer_conf
            self._slicer_gcode = self._settings.get(["slicer_gcode"])
            self._pw = re.compile(self._settings.get(["pw"]))
            self._pd = re.compile(self._settings.get(["pd"]))
            self._ph = re.compile(self._settings.get(["ph"]))
            self._pm = re.compile(self._settings.get(["pm"]))
            self._ps = re.compile(self._settings.get(["ps"]))

            self._pwp = int(self._settings.get(["pwp"]))
            self._pdp = int(self._settings.get(["pdp"]))
            self._php = int(self._settings.get(["php"]))
            self._pmp = int(self._settings.get(["pmp"]))
            self._psp = int(self._settings.get(["psp"]))

            self._search_mode = self._settings.get(["search_mode"])
            self._search_pattern = self._settings.get(["search_pattern"])
        else:
            self._set_slicer_settings(int(self._slicer_conf))


    def _set_slicer_settings(self, slicer):
        self._slicer = slicer
        self._slicer_gcode = self._slicer_def[int(slicer)][0]
        self._pw = re.compile(self._slicer_def[int(slicer)][1])
        self._pd = re.compile(self._slicer_def[int(slicer)][2])
        self._ph = re.compile(self._slicer_def[int(slicer)][3])
        self._pm = re.compile(self._slicer_def[int(slicer)][4])
        self._ps = re.compile(self._slicer_def[int(slicer)][5])

        self._pwp = self._slicer_def[int(slicer)][6]
        self._pdp = self._slicer_def[int(slicer)][7]
        self._php = self._slicer_def[int(slicer)][8]
        self._pmp = self._slicer_def[int(slicer)][9]
        self._psp = self._slicer_def[int(slicer)][10]

        self._search_mode = self._slicer_def[int(slicer)][11]
        self._search_pattern = self._slicer_def[int(slicer)][12]


# SECTION: Estimation
    def updateGcodeEstimation(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if self._estimator is None:
            return

        if self._search_mode == "GCODE" and gcode and gcode == self._slicer_gcode:
            self._logger.debug("SlicerEstimator: {} found - {}".format(gcode,cmd))
            estimated_time = self._parseEstimation(cmd)
            if estimated_time:
                self._estimator.estimated_time = estimated_time
        else:
            return


    # calculate estimation on print progress
    def on_print_progress(self, storage, path, progress):
        if self._search_mode == "COMMENT":
            if self._slicer_estimation:
                self._estimator.estimated_time = self._slicer_estimation - (self._slicer_estimation * progress * 0.01)
                self._logger.debug("SlicerEstimator: {}sec".format(self._estimator.estimated_time))


    # estimator factory hook
    def estimator_factory(self):
        def factory(*args, **kwargs):
            self._estimator = SlicerEstimator(*args, **kwargs)
            self._estimator.average_prio = self._average_prio
            return self._estimator
        return factory


    # EventHandlerPlugin for native information search
    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED:
            origin = payload["origin"]
            path = payload["path"]
            if origin == "local":
                if self._metadata:
                    self._send_metadata_print_event(origin, path)
                self._set_slicer(origin, path)
                if self._search_mode == "COMMENT":
                    self._logger.debug("Search started in file {}".format(path))
                    self._executor.submit(
                        self._search_slicer_comment_file, origin, path
                    )
        if event == Events.PRINT_CANCELLED or event == Events.PRINT_FAILED or event == Events.PRINT_DONE:
            # Init of Class variables for new estimation
            self._slicer_estimation = None
            self._sliver_estimation_str = None
            self._estimator.estimated_time = -1
            self._logger.debug("Event received: {}".format(event))
        if event == Events.FILE_ADDED and self._metadata:
            if payload["storage"] == "local" and payload["type"][1] == "gcode":
                self._logger.debug("File uploaded and will be scanned for Metadata")
                self._find_metadata(payload["storage"], payload["path"])


# SECTION: File metadata
    # search for material data
    def _find_metadata(self, origin, path):
        # Format: ;Slicer info:<key>;<Displayname>;<Value>
        results = self._search_in_file_start_all(origin, path, ";Slicer info:", 5000)
        if results is not None:
            filament = dict()
            for result in results:
                slicer_info = result[13:].rstrip("\n").split(";")
                if len(slicer_info) == 3:
                    # old format
                    filament[slicer_info[0]] = slicer_info[2].strip()
                else:
                    filament[slicer_info[0]] = slicer_info[1].strip()

        self._file_manager._storage_managers[origin].set_additional_metadata(path, "slicer", filament, overwrite=True)
        self._logger.debug(self._file_manager._storage_managers[origin].get_additional_metadata(path,"slicer"))


    # Update all metadata in files
    def _update_metadata_in_files(self):
        results =  self._file_manager._storage_managers["local"].list_files(recursive=True)
        # TODO: Verzeichnisse werden nicht verarbeitet.
        if results is not None:
            for resultKey in results:
                if results[resultKey]["type"] == "machinecode":
                    path = results[resultKey]["path"]
                    self._file_manager._storage_managers["local"].remove_additional_metadata(path, "slicer")
                    self._find_metadata("local", path)


# SECTION: Estimation helper
    # set the slicer before starting the print, fallback to config if fails
    def _set_slicer(self, origin, path):
        if self._slicer_auto:
            slicer_detected = self._detect_slicer(origin, path)
            if slicer_detected:
                self._set_slicer_settings(slicer_detected)
            else:
                self._set_slicer_settings(self._slicer_conf)


   # slicer auto selection
    def _detect_slicer(self, origin, path):
        line = self._search_in_file_regex(origin, path,".*(PrusaSlicer|Simplify3D|Cura_SteamEngine).*")
        if line:
            if  "Cura_SteamEngine" in line:
                self._logger.info("Detected Cura")
                return 2
            elif "PrusaSlicer" in line:
                self._logger.info("Detected PrusaSlicer")
                return 1
            elif "Simplify3D" in line:
                self._logger.info("Detected Simplify3D")
                return 3
        else:
            self._logger.warning("Autoselection of slicer not successful!")


    def _parseEstimation(self,cmd):
        if self._pw.pattern != "":
            mw = self._pw.match(cmd)
        else:
            mw = None
        if self._pd.pattern != "":
            md = self._pd.match(cmd)
        else:
            md = None
        if self._ph.pattern != "":
            mh = self._ph.match(cmd)
        else:
            mh = None
        if self._pm.pattern != "":
            mm = self._pm.match(cmd)
        else:
            mm = None
        if self._ps.pattern != "":
            ms = self._ps.match(cmd)
        else:
            ms = None

        if mw or md or mh or mm or ms:
            if mw:
                weeks = float(mw.group(self._pwp))
            else:
                weeks = 0
            if md:
                days = float(md.group(self._pdp))
            else:
                days = 0
            if mh:
                hours = float(mh.group(self._php))
            else:
                hours = 0
            if mm:
                minutes = float(mm.group(self._pmp))
            else:
                minutes = 0
            if ms:
                seconds = float(ms.group(self._psp))
            else:
                seconds = 0
            self._logger.debug("SlicerEstimator: Weeks {}, Days {}, Hours {}, Minutes {}, Seconds {}".format(weeks, days, hours, minutes, seconds))
            estimated_time = weeks*7*24*60*60 + days*24*60*60 + hours*60*60 + minutes*60 + seconds
            self._logger.debug("SlicerEstimator: {}sec".format(estimated_time))
            return estimated_time
        else:
            self._logger.debug("SlicerEstimator: unknown cmd {}".format(cmd))


    # file search slicer comment
    def _search_slicer_comment_file(self, origin, path):
        self._slicer_estimation = None
        slicer_estimation_str = self._search_in_file_regex(origin, path, self._search_pattern)

        if slicer_estimation_str:
            self._logger.debug("Slicer-Comment {} found.".format(slicer_estimation_str))
            self._slicer_estimation = self._parseEstimation(slicer_estimation_str)
            self._estimator.estimated_time = self._slicer_estimation
        else:
            self._logger.warning("Slicer-Comment not found. Please check if you selected the correct slicer.")


    # generic file search with RegEx
    def _search_in_file_regex(self, origin, path, pattern, rows = 0):
        path_on_disk = self._file_manager.path_on_disk(origin, path)
        self._logger.debug("Path on disc searched: {}".format(path_on_disk))
        compiled = re.compile(pattern)
        steps = rows
        with io.open(path_on_disk, mode="r", encoding="utf8", errors="replace") as f:
            for line in f:
                if compiled.match(line):
                    return line

                if rows > 0:
                    steps -= 1
                    if steps <= 0:
                        break


    # generic file search and find all occurences beginning with
    def _search_in_file_start_all(self, origin, path, pattern, rows = 0):
        path_on_disk = self._file_manager.path_on_disk(origin, path)
        self._logger.debug("Path on disc searched: {}".format(path_on_disk))
        steps = rows

        return_arr = []
        with io.open(path_on_disk, mode="r", encoding="utf8", errors="replace") as f:
            for line in f:
                if line[:len(pattern)] == pattern:
                    return_arr.append(line)
                if rows > 0:
                    steps -= 1
                    if steps <= 0:
                        return return_arr
        return return_arr



# SECTION: Analysis Queue Estimation (file upload)
    def analysis_queue_factory(self, *args, **kwargs):
        return dict(gcode=lambda finished_callback: SlicerEstimatorGcodeAnalysisQueue(finished_callback, self))

    def run_analysis(self, path):
        self._set_slicer("local", path)
        self._logger.debug("Search started in file {}".format(path))
        slicer_estimation_str = self._search_in_file_regex("local", path, self._search_pattern)
        if slicer_estimation_str:
            self._logger.debug("Slicer-Estimation {} found.".format(slicer_estimation_str))
            return self._parseEstimation(slicer_estimation_str)
        else:
            self._logger.warning("Slicer-Estimation not found. Please check if you selected the correct slicer.")


# SECTION: API
    def register_plugin(self, plugin_identifier, plugin_name):
        """Register a plugin to add it to the setting

        Args:
            plugin_identifier (String): OctoPrint Plugin Identifier
            plugin_name (String): OctoPrints plugins name (or any other name you like to use)
        """
        if plugin_identifier in self._plugins:
            self._logger.debug("Plugin {} already registered".format(plugin_identifier))
        else:
            self._logger.debug("Plugin {} registered".format(plugin_identifier))
            self._plugins[plugin_identifier] = dict()
            self._plugins[plugin_identifier]["name"] = plugin_name
            self._plugins[plugin_identifier]["targets"] = dict()
            self._settings.set(["plugins"], self._plugins)


    def register_plugin_target(self, plugin_identifier, target, target_name):
        """Register a target to an existing plugin - call multiple time for new targets

        Args:
            plugin_identifier (String): OctoPrint Plugin Identifier
            target (String): ID of a target (you can choose)
            target_name (String): Name of a target to use in the dropdown
        """
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
        for meta_items in self._metadata_list:
            if meta_items["targets"][plugin_identifier][target].pop() is None:
                self._logger.error("Could not unregister plugins {} target {}!".format(plugin_identifier, target))
            self._settings.set(["metadata_list"], self._metadata_list)
        self._logger.info("Plugin {} unregistered target {}".format())


    def get_registered_plugins(self):
        """Return list of plugins registered

        Returns:
            array of strings: List of plugin identifiers registered
        """
        return self._plugins.keys()


    def get_registered_plugin_targets(self, plugin_identifier):
        """Returns list of targets registered for a plugin

        Args:
            plugin_identifier (String)): plugin_identifier to check

        Returns:
            array of strings: List of targets registered for a plugin
        """
        if self._plugins[plugin_identifier] is None:
            return None
        else:
            return self._plugins[plugin_identifier]["targets"].keys()


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
                for meta_item in meta_selected:
                    return_item = [meta_item["id"], meta_item["description"], self._file_manager._storage_managers[origin].get_additional_metadata(path, "slicer")[meta_item["id"]]]
                    return_list.append(return_item)
                return return_list
            else:
                self._logger.error("Target {} of plugin {} not registered.".format(target, plugin_identifier))
        else:
            self._logger.error("Plugin {} not registered.".format(plugin_identifier))


    def _send_metadata_print_event(self, origin, path):
        event = Events.PLUGIN__SLICER_ESTIMATOR_METADATA_PRINT
        custom_payload = dict()
        for plugin in self._plugins:
            custom_payload[plugin] = dict()
            for target in self._plugins[plugin]["targets"]:
                custom_payload[plugin][target] = self.get_metadata_file(origin, path, plugin, target)
        self._logger.info("Send Metadata Print Event for file {}".format(path))       
        self._event_bus.fire(event, payload=custom_payload)


    def register_custom_events(*args, **kwargs):
        return ["metadata_print"]


    # def get_api_commands(self):
    #     return dict(get_filament_data = [])


    # def on_api_command(self, command, data):
    #     import flask
    #     import json
    #     from octoprint.server import user_permission
    #     if not user_permission.can():
    #         return flask.make_response("Insufficient rights", 403)

    #     if command == "get_filament_data":
    #         FileList = self._file_manager.list_files(recursive=True)
    #         self._logger.debug(FileList)
    #         localfiles = FileList["local"]
    #         results = filament_key = dict()
    #         for key, file in localfiles.items():
    #             if localfiles[key]["type"] == 'machinecode':
    #                 filament_meta = self._file_manager._storage_managers['local'].get_additional_metadata(localfiles[key]["path"] ,"filament")
    #                 results[localfiles[key]["path"]] = filament_meta
    #         return flask.jsonify(results)


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


# SECTION: Analysis Queue Class
class SlicerEstimatorGcodeAnalysisQueue(GcodeAnalysisQueue):
    def __init__(self, finished_callback, plugin):
        super(SlicerEstimatorGcodeAnalysisQueue, self).__init__(finished_callback)
        self._plugin = plugin
        self._result_slicer = None

    def _do_analysis(self, high_priority=False):
        try: # run a standard analysis and update estimation if found in GCODE
            result = super(SlicerEstimatorGcodeAnalysisQueue, self)._do_analysis(high_priority)
            if self._plugin.estimate_upload and not self._aborted:
                future = self._plugin._executor.submit(
                    self._run_analysis, self._current.path
                )
                # Break analysis of abort requested
                while not future.done() and not self._aborted:
                    time.sleep(1)
                if future.done() and self._result_slicer:
                    self._logger.info("Found {}s from slicer for file {}".format(self._result_slicer, self._current.name))
                    result["estimatedPrintTime"] = self._result_slicer
                elif not future.done() and self._aborted:
                    future.shutdown(wait=False)
                    raise AnalysisAborted(reenqueue=self._reenqueue)
                return result
        except AnalysisAborted as _:
            self._logger.info("Probably starting printing, aborting analysis of file-upload.")
            raise

    def _do_abort(self, reenqueue=True):
        super(SlicerEstimatorGcodeAnalysisQueue, self)._do_abort(reenqueue)

    def _run_analysis(self, path):
        self._result_slicer = self._plugin.run_analysis(path)
        
        

__plugin_name__ = "Slicer Estimator"
__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

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
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.updateGcodeEstimation,
        "octoprint.printer.estimation.factory": __plugin_implementation__.estimator_factory,
        "octoprint.filemanager.analysis.factory": __plugin_implementation__.analysis_queue_factory,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.events.register_custom_events": __plugin_implementation__.register_custom_events
    }
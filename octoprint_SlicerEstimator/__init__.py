# coding=utf-8
from __future__ import absolute_import, unicode_literals
from concurrent.futures import ThreadPoolExecutor
from octoprint.printer.estimation import PrintTimeEstimator

import octoprint.plugin
import octoprint.events
import re
import sarge
import io

from octoprint.printer.estimation import PrintTimeEstimator


class SlicerEstimator(PrintTimeEstimator):
    def __init__(self, job_type):
        PrintTimeEstimator.__init__(self, job_type)
        self._job_type = job_type
        self.estimated_time = 0


    def estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
        if self._job_type != "local":
            return PrintTimeEstimator.estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType)
        return self.estimated_time, "estimate"


class SlicerEstimatorPlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.TemplatePlugin, octoprint.plugin.SettingsPlugin, octoprint.plugin.EventHandlerPlugin, octoprint.plugin.ProgressPlugin):
    def __init__(self):
        self._estimator = None
        self._slicer_estimation = None
        self._executor = ThreadPoolExecutor()

    # Settings
    def on_after_startup(self):
        self._logger.info("Started up SlicerEstimator")
        
        #Slicer defaults - actual Cura, Slic3r Prusa Edition, Cura Native, Simplify3D
        self._slicer_def = [
                ["M117","","",
                "M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
                "M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
                "M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
                1,1,1,2,3,"GCODE",""],
                ["M73","","",
                "",
                "M73 P([0-9]+) R([0-9]+)",
                "",
                1,1,1,2,1,"GCODE",""],
                ["","","",
                "",
                "",
                ";TIME:([0-9]+)",
                1,1,1,1,1,"COMMENT",";TIME:([0-9]+)"],
                ["","","",
                ";   Build time: ([0-9]+) hour ([0-9]+) minutes",
                ";   Build time: ([0-9]+) hour ([0-9]+) minutes",
                "",
                1,1,1,2,1,"COMMENT",";   Build time: ([0-9]+) hour ([0-9]+) minutes"]]
        self._update_settings_from_config()


    def _update_settings_from_config(self):
        self._slicer_conf = self._settings.get(["slicer"])
        self._logger.debug("SlicerEstimator: Slicer Setting {}".format(self._slicer_conf))

        if self._slicer_conf == "c": 
            self.slicer = self._slicer_conf 
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
            self._search_mode = self._settings.get(["search_pattern"])
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



    def get_settings_defaults(self):
        return dict(slicer="a",
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
                    search_pattern="")


    def on_settings_save(self, data):  
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._update_settings_from_config()


    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]


    ##~~ queuing gcode hook

    def updateGcodeEstimation(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if self._estimator is None:
            return

        if self._search_mode == "GCODE" and gcode and gcode == self._slicer_gcode:
            self._logger.debug("SlicerEstimator: {} found - {}".format(gcode,cmd))
            self._estimator.estimated_time = self._parseEstimation(cmd)
        else:
            return


    ##~~ calculate estimation on print progress

    def on_print_progress(self, storage, path, progress):
        if self._search_mode == "COMMENT":
            if self._slicer_estimation:
                self._estimator.estimated_time = self._slicer_estimation - (self._slicer_estimation * progress * 0.01)
                self._logger.debug("SlicerEstimator: {}sec".format(self._estimator.estimated_time))


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


    ##~~ estimator factory hook

    def estimator_factory(self):
        def factory(*args, **kwargs):
            self._estimator = SlicerEstimator(*args, **kwargs)
            return self._estimator
        return factory


    ##~~ EventHandlerPlugin for native information search

    def on_event(self, event, payload):
        if event == octoprint.events.Events.PRINT_STARTED:
            if payload["origin"] == "local":
                if self._search_mode == "COMMENT":
                    self._logger.debug("Search started in file {}".format(payload["path"]))
                    self._executor.submit(
                        self._search_slicer_comment_file, payload["origin"], payload["path"]
                    )


    ##~~ file search

    def _search_slicer_comment_file(self, origin, path):
        self._slicer_estimation = ""
        slicer_estimation_str = self._search_through_file(origin, path, self._search_pattern)

        if slicer_estimation_str:
            self._logger.debug("Slicer-Comment {} found.".format(slicer_estimation_str))
            self._slicer_estimation = self._parseEstimation(slicer_estimation_str)
            self._estimator.estimated_time = self._slicer_estimation


    def _search_through_file(self, origin, path, pattern):
        path_on_disk = self._file_manager.path_on_disk(origin, path)
        self._logger.debug("Path on disc searched: {}".format(path_on_disk))
        compiled = re.compile(pattern)
        with io.open(path_on_disk, mode="r", encoding="utf8", errors="replace") as f:
            for line in f:
                if compiled.match(line):
                    return line


    ##~~ software update hook

    def get_update_information(self):
        return dict(
            SlicerEstimator=dict(
                displayName=self._plugin_name,
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="NilsRo",
                repo="OctoPrint-SlicerEstimator",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/NilsRo/OctoPrint-SlicerEstimator/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "Slicer Print Time Estimator"
__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3
__plugin_implementation__ = SlicerEstimatorPlugin()
__plugin_hooks__ = {
    "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.updateGcodeEstimation,
    "octoprint.printer.estimation.factory": __plugin_implementation__.estimator_factory,
    "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}

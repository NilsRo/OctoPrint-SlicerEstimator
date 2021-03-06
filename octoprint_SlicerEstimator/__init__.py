# coding=utf-8
from __future__ import absolute_import, unicode_literals
from concurrent.futures import ThreadPoolExecutor
from octoprint.printer.estimation import PrintTimeEstimator

import octoprint.plugin
import octoprint.events
import re
import sarge
import io
import time

from octoprint.filemanager.analysis import AnalysisAborted
from octoprint.filemanager.analysis import GcodeAnalysisQueue
from octoprint.printer.estimation import PrintTimeEstimator


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
                            octoprint.plugin.AssetPlugin):
    def __init__(self):
        self._estimator = None
        self._slicer_estimation = None
        self._executor = ThreadPoolExecutor()


        #Slicer defaults - actual Cura M117, PrusaSlicer, Cura, Simplify3D
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
        self._update_settings_from_config()


    def get_settings_defaults(self):
        return dict(slicer="2",
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
                    estimate_upload=True)


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
        if event == octoprint.events.Events.PRINT_STARTED:
            if payload["origin"] == "local":
                self._set_slicer(payload["origin"], payload["path"])
                if self._search_mode == "COMMENT":
                    self._logger.debug("Search started in file {}".format(payload["path"]))
                    self._executor.submit(
                        self._search_slicer_comment_file, payload["origin"], payload["path"]
                    )
        if event == octoprint.events.Events.PRINT_CANCELLED or event == octoprint.events.Events.PRINT_FAILED or event == octoprint.events.Events.PRINT_DONE:
            # Init of Class variables for new estimation
            self._slicer_estimation = None
            self._sliver_estimation_str = None
            self._estimator.estimated_time = -1
            self._logger.debug("Event received: {}".format(event))


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
        line = self._search_through_file(origin, path,".*(PrusaSlicer|Simplify3D|Cura_SteamEngine).*")
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
        slicer_estimation_str = self._search_through_file(origin, path, self._search_pattern)

        if slicer_estimation_str:
            self._logger.debug("Slicer-Comment {} found.".format(slicer_estimation_str))
            self._slicer_estimation = self._parseEstimation(slicer_estimation_str)
            self._estimator.estimated_time = self._slicer_estimation
        else:
            self._logger.warning("Slicer-Comment not found. Please check if you selected the correct slicer.")


    # generic file search with RegEx
    def _search_through_file(self, origin, path, pattern):
        path_on_disk = self._file_manager.path_on_disk(origin, path)
        self._logger.debug("Path on disc searched: {}".format(path_on_disk))
        compiled = re.compile(pattern)
        with io.open(path_on_disk, mode="r", encoding="utf8", errors="replace") as f:
            for line in f:
                if compiled.match(line):
                    return line


# SECTION: Analysis Queue Estimation (file upload)
    def analysis_queue_factory(self, *args, **kwargs):
        return dict(gcode=lambda finished_callback: SlicerEstimatorGcodeAnalysisQueue(finished_callback, self))

    def run_analysis(self, path):
        self._set_slicer("local", path)
        self._logger.debug("Search started in file {}".format(path))
        slicer_estimation_str = self._search_through_file("local", path, self._search_pattern)
        if slicer_estimation_str:
            self._logger.debug("Slicer-Estimation {} found.".format(slicer_estimation_str))
            return self._parseEstimation(slicer_estimation_str)
        else:
            self._logger.warning("Slicer-Estimation not found. Please check if you selected the correct slicer.")
            


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

__plugin_name__ = "Slicer Print Time Estimator"
__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3
__plugin_implementation__ = SlicerEstimatorPlugin()
__plugin_hooks__ = {
    "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.updateGcodeEstimation,
    "octoprint.printer.estimation.factory": __plugin_implementation__.estimator_factory,
    "octoprint.filemanager.analysis.factory": __plugin_implementation__.analysis_queue_factory,
    "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}

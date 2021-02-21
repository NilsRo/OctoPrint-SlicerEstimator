# coding=utf-8
from __future__ import absolute_import, unicode_literals

import octoprint.plugin

import re

from octoprint.printer.estimation import PrintTimeEstimator


class M117_estimator(PrintTimeEstimator):
    def __init__(self, job_type):
        PrintTimeEstimator.__init__(self, job_type)
        self._job_type = job_type
        self.estimated_time = 0
        self.percentage_done = -1

    def estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
        if self._job_type != "local" or self.percentage_done == -1:
            return PrintTimeEstimator.estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType)
        return self.estimated_time, "estimate"

class M117_estimatorPlugin(octoprint.plugin.StartupPlugin, octoprint.plugin.TemplatePlugin, octoprint.plugin.SettingsPlugin):
    pc = re.compile("M73 P([0-9]+)")

    def __init__(self):
        self._estimator = None


    # Settings
    def on_after_startup(self):
        self._logger.info("Started up M117_estimator")        
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

    def get_settings_defaults(self):
        return dict(pw="",
                    pd="",
                    ph="M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
                    pm="M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
                    ps="M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s",
                    pwp=1,
                    pdp=1,
                    php=1,
                    pmp=2,
                    psp=3)

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]


    ##~~ queuing gcode hook

    def updateEstimation(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if self._estimator is None:
            return

        if gcode and gcode == "M73":
            self._logger.debug("M117_estimator: M73 found")

            mp = self.pc.match(cmd)
            if mp:
                self._estimator.percentage_done = float(mp.group(1))

                self._logger.debug("M117_estimator: {}% {}sec".format(self._estimator.percentage_done, self._estimator.estimated_time))
            else:
                self._logger.debug("M117_estimator: unknown cmd {}".format(cmd))

        if gcode and gcode == "M117":
            self._logger.debug("M117_estimator: M117 found")

            mw = self._pw.match(cmd)
            md = self._pd.match(cmd)
            mh = self._ph.match(cmd)
            mm = self._pm.match(cmd)
            ms = self._ps.match(cmd)

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

                self._logger.debug("M117_estimator: Weeks {}, Days {}, Hours {}, Minutes {}, Seconds {}".format(weeks, days, hours, minutes, seconds))
                self._estimator.estimated_time = weeks*7*24*60*60 + days*24*60*60 + hours*60*60 + minutes*60 + seconds
                self._logger.debug("M117_estimator: {}% {}sec".format(self._estimator.percentage_done, self._estimator.estimated_time))
            else:
                self._logger.debug("M117_estimator: unknown cmd {}".format(cmd))


    ##~~ estimator factory hook

    def estimator_factory(self):
        def factory(*args, **kwargs):
            self._estimator = M117_estimator(*args, **kwargs)
            return self._estimator
        return factory

    ##~~ software update hook

    def get_update_information(self):
        return dict(
            M117_estimator=dict(
                displayName=self._plugin_name,
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="NilsRo",
                repo="OctoPrint-M117_estimator",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/NilsRo/OctoPrint-M117_estimator/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "M117 Print Time Estimator"
__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3
__plugin_implementation__ = M117_estimatorPlugin()
__plugin_hooks__ = {
    "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.updateEstimation,
    "octoprint.printer.estimation.factory": __plugin_implementation__.estimator_factory,
    "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}

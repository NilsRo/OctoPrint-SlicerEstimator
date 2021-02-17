# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin

import re

from octoprint.printer.estimation import PrintTimeEstimator


class GcodestatPrintTimeEstimator(PrintTimeEstimator):
    def __init__(self, job_type):
        PrintTimeEstimator.__init__(self, job_type)
        self._job_type = job_type
        self.estimated_time = 0
        self.percentage_done = -1

    def estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
        if self._job_type != "local" or self.percentage_done == -1:
            return PrintTimeEstimator.estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType)
        return self.estimated_time, "estimate"

class GcodestatPrintTimeEstimatorPlugin(octoprint.plugin.StartupPlugin):

    ph = re.compile('M117 Time Left ([0-9]+)h([0-9]+)m([0-9]+)s')
    pc = re.compile('M73 P([0-9]+)')

    def __init__(self):
        self._estimator = None

    def on_after_startup(self):
        self._logger.info("Started up gcodestatEstimator Cura")


    ##~~ queuing gcode hook

    def updateEstimation(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if (self._estimator is None:
            return

        if (gcode == "M73" ):
            self._logger.debug("gcodestatEstimator: M73 found")

            mp = self.pc.match(cmd)
            self._estimator.percentage_done = float(mp.group(1))

        if (gcode == "M117"):
            self._logger.debug("gcodestatEstimator: M117 found")

            mh = self.ph.match(cmd)
            self._estimator.estimated_time = float(mh.group(1))*60*60 + float(mh.group(2))*60 + float(mh.group(3))

        self._logger.debug("gcodestatEstimator: {}% {}sec".format(self._estimator.percentage_done, self._estimator.estimated_time))

    ##~~ estimator factory hook

    def estimator_factory(self):
        def factory(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
            self._estimator = GcodestatPrintTimeEstimator(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType)
            return self._estimator
        return factory

    ##~~ software update hook

    def get_update_information(self):
        return dict(
            gcodestatEstimator=dict(
                displayName=self._plugin_name,
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="NilsRo",
                repo="OctoPrint-gcodestatEstimator",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/NilsRo/OctoPrint-gcodestatEstimator/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "gcodestatEstimator-Cura"
__plugin_pythoncompat__ = ">=2.7,<4"

__plugin_implementation__ = GcodestatPrintTimeEstimatorPlugin()
__plugin_hooks__ = {
    "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.updateEstimation,
    "octoprint.printer.estimation.factory": __plugin_implementation__.estimator_factory,
    "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}

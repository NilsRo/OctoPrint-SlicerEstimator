# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin

import re

from octoprint.printer.estimation import PrintTimeEstimator

class GcodestatPrintTimeEstimator(
                                    octoprint.plugin.StartupPlugin,
                                    octoprint.plugin.EventHandlerPlugin,
                                    octoprint.plugin.AssetPlugin,
                                    octoprint.plugin.TemplatePlugin,
                                    octoprint.plugin.SettingsPlugin,
                                    PrintTimeEstimator):
    estimatedTime  = 0
    percentageDone = -1
    
    # this could probbly be done trough single regex but I just don't have any more patience
    ph = re.compile('M117 ([0-9]+)%+ Remaining \( ([0-9]+):([0-9]+):([0-9]+) \)')
    pm = re.compile('M117 ([0-9]+)%+ Remaining \( ([0-9]+):([0-9]+) \)')
    ps = re.compile('M117 ([0-9]+)%+ Remaining \( ([0-9]+) \)')

    def __init__(self, job_type):
        GcodestatPrintTimeEstimator.estimatedTime  = 0
        GcodestatPrintTimeEstimator.percentageDone = -1
        PrintTimeEstimator.__init__(self, job_type)
        self._job_type = job_type

    def on_after_startup(self):
        self._logger.info("Started up gcodestatEstimator")
        
    def estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
        if self._job_type != "local":
          return PrintTimeEstimator.estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType)

        if GcodestatPrintTimeEstimator.percentageDone == -1: 
          return PrintTimeEstimator.estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType)
        
        return GcodestatPrintTimeEstimator.estimatedTime, "estimate"

    def updateEstimation (self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if gcode and cmd.startswith("M117"):
           self._logger.info("gcodestatEstimator: M117 found")
# what is wrong with python ?!?!?!             
#           if m = GcodestatPrintTimeEstimator.ph.match(cmd):
#              GcodestatPrintTimeEstimator.estimatedTime = float(m.group(2))*60*60 + float(m.group(3))*60 + float(m.group(4))
#              GcodestatPrintTimeEstimator.percentageDone = float(m.group(1))
#           elif m = GcodestatPrintTimeEstimator.pm.match(cmd):
#              GcodestatPrintTimeEstimator.estimatedTime = float(m.group(2))*60 + float(m.group(3))
#              GcodestatPrintTimeEstimator.percentageDone = float(m.group(1))
#           elif m = GcodestatPrintTimeEstimator.ps.match(cmd):
#              GcodestatPrintTimeEstimator.estimatedTime = float(m.group(2))
#              GcodestatPrintTimeEstimator.percentageDone = float(m.group(1))
#           else :
#              self._logger.info("gcodestatEstimator: NO MATCH!")
           mh = GcodestatPrintTimeEstimator.ph.match(cmd)
           mm = GcodestatPrintTimeEstimator.pm.match(cmd)
           ms = GcodestatPrintTimeEstimator.ps.match(cmd)
           if mh:
              GcodestatPrintTimeEstimator.estimatedTime = float(mh.group(2))*60*60 + float(mh.group(3))*60 + float(mh.group(4))
              GcodestatPrintTimeEstimator.percentageDone = float(mh.group(1))
              self._logger.info("gcodestatEstimator: "+ str(GcodestatPrintTimeEstimator.percentageDone) + "% " + str(GcodestatPrintTimeEstimator.estimatedTime) + "sec")
           elif mm:
              GcodestatPrintTimeEstimator.estimatedTime = float(mm.group(2))*60 + float(mm.group(3))
              GcodestatPrintTimeEstimator.percentageDone = float(mm.group(1))
              self._logger.info("gcodestatEstimator: "+ str(GcodestatPrintTimeEstimator.percentageDone) + "% " + str(GcodestatPrintTimeEstimator.estimatedTime) + "sec")
           elif ms:
              GcodestatPrintTimeEstimator.estimatedTime = float(ms.group(2))
              GcodestatPrintTimeEstimator.percentageDone = float(ms.group(1))
              self._logger.info("gcodestatEstimator: "+ str(GcodestatPrintTimeEstimator.percentageDone) + "% " + str(GcodestatPrintTimeEstimator.estimatedTime) + "sec")
           else :
              self._logger.info("gcodestatEstimator: NO MATCH!")

           
        return


def create_estimator_factory(*args, **kwargs):
    return GcodestatPrintTimeEstimator

__plugin_name__ = "OctoPrint-gcodestatEstimator"
__plugin_implementation__ = GcodestatPrintTimeEstimator(None)
__plugin_hooks__ = {
  "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.updateEstimation,
  "octoprint.printer.estimation.factory": create_estimator_factory
}

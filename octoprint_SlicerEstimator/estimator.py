import time
from .const import *
from asyncio.log import logger
from octoprint.printer.estimation import PrintTimeEstimator
from octoprint.filemanager.analysis import AnalysisAborted
from octoprint.filemanager.analysis import GcodeAnalysisQueue

class SlicerEstimator(PrintTimeEstimator):
    def __init__(self, job_type):
        PrintTimeEstimator.__init__(self, job_type)
        self._job_type = job_type
        self.estimated_time = -1.0
        self.average_prio = False
        self.time_left = -1.0
        self.cleaned_print_time = -1.0


    def estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType):
        std_estimator = PrintTimeEstimator.estimate(self, progress, printTime, cleanedPrintTime, statisticalTotalPrintTime, statisticalTotalPrintTimeType)
        self.cleaned_print_time = cleanedPrintTime

        if self._job_type != "local" or self.estimated_time == -1.0 or cleanedPrintTime is None or progress is None:
            # using standard estimator
            return std_estimator
        elif std_estimator[1] == "average" and self.average_prio:
            # average more important than estimation
            return std_estimator
        else:
            # return "slicerestimator" as Origin of estimation
            logger.debug("SlicerEstimator: Estimation Reported {}".format(self.time_left))
            return self.estimated_time, "slicerestimator"
        
       
class SlicerEstimatorGcodeAnalysisQueue(GcodeAnalysisQueue):    
    def __init__(self, finished_callback, plugin):
        super(SlicerEstimatorGcodeAnalysisQueue, self).__init__(finished_callback)
        self._plugin = plugin


    def _do_analysis(self, high_priority=False):
        try: # run a standard analysis and update estimation if found in GCODE
            result = super(SlicerEstimatorGcodeAnalysisQueue, self)._do_analysis(high_priority)
            if not self._aborted:
                future = self._plugin._executor.submit(
                    self._run_analysis, self._current.path
                )
                # Break analysis of abort requested
                while not future.done() and not self._aborted:
                    time.sleep(1)
                if future.done():
                    slicer_additional = self._plugin._file_manager._storage_managers["local"].get_additional_metadata(self._current.path,"slicer_additional")
                    if slicer_additional:
                        result["estimatedPrintTime"] = slicer_additional["printtime"]
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
from ast import Constant
import re
import logging
import octoprint.filemanager
import octoprint.filemanager.storage
import octoprint.filemanager.util


from .const import *
from .util import *


class SlicerEstimatorMetadataFiles:
    
    def __init__(self, plugin):
        self._plugin = plugin
        self._file_manager = self._plugin._file_manager
        self._origin = "local"
      
    # Delete metadata in all files      
    def delete_metadata_in_files(self):
        results = self._file_manager._storage_managers[self._origin].list_files(recursive=True)        
        if results is not None:
            filelist = SlicerEstimatorFileHandling.flatten_files(results)
            for path in filelist:
                self._file_manager._storage_managers[self._origin].remove_additional_metadata(path, "slicer_metadata")
        return filelist
        
    # Update metadata in all files   
    def update_metadata_in_files(self):
        results = self._file_manager._storage_managers[self._origin].list_files(recursive=True)        
        if results is not None:
            filelist = SlicerEstimatorFileHandling.flatten_files(results)
            for path in filelist:
                self._file_manager._storage_managers[self._origin].remove_additional_metadata(path, "slicer_metadata")
                path_on_disk = self._file_manager._storage_managers[self._origin].path_on_disk(path)
                slicer = SlicerEstimatorMetadataFiles.detect_slicer(path_on_disk)
                if slicer is not None:
                    results = SlicerEstimatorFileHandling.return_file_lines(path_on_disk)
                    if results is not None:
                        metadata_obj = SlicerEstimatorMetadata("local", path, slicer, self._plugin)             
                        for result in results:
                            metadata_obj.process_metadata_line(result)
                        metadata_obj.store_metadata()
            return filelist

                
    # slicer auto selection
    def detect_slicer(path):
        line = SlicerEstimatorFileHandling.search_in_file_regex(path,".*(PrusaSlicer|SuperSlicer|Simplify3D|Cura_SteamEngine|Creality Slicer|OrcaSlicer).*")
        if line:
            if  "Cura_SteamEngine" in line or "Creality Slicer" in line:
                return SLICER_CURA
            elif "PrusaSlicer" in line:
                return SLICER_PRUSA
            elif "SuperSlicer" in line:
                return SLICER_SUPERSLICER            
            elif "Simplify3D" in line:
                return SLICER_SIMPLIFY3D
            elif "OrcaSlicer" in line:
                return SLICER_ORCA
            else: 
                return None


class SlicerEstimatorMetadata:
    def __init__(self, origin, path, slicer, plugin):        
        self._origin = origin
        self._path = path
        self._plugin = plugin   
        self._file_manager = self._plugin._file_manager
        self._slicer = slicer  
        self._logger = logging.getLogger("octoprint.plugins.SlicerEstimator")
        self._metadata = dict()           
        if self._slicer == SLICER_PRUSA or self._slicer == SLICER_SUPERSLICER or self._slicer == SLICER_ORCA:
            self._metadata_regex = re.compile("^; (\w*) = (.*)")
        elif self._slicer == SLICER_SIMPLIFY3D:
            self._metadata_regex = re.compile("^;   (\w*),(.*)")        
 
        
    # Save gathered information to OctoPrint file metadata
    def store_metadata(self):
        self._file_manager._storage_managers["local"].set_additional_metadata(self._path, "slicer_metadata", self._metadata, overwrite=True)     
        self._logger.debug("File: {} - metadata written: {}".format(self._path, self._file_manager._storage_managers["local"].get_additional_metadata(self._path,"slicer_metadata")))         

                
    # get metadata from line
    def process_metadata_line(self, decoded_line):
        # standard format for slicers
        # Cura: no standard format for metadata
        # Prusa/SuperSlicer/OrcaSlicer: ; bridge_angle = 0
        # Simplify3D: ;   layerHeight,0.2
        if decoded_line[:13] == ";Slicer info:":
            slicer_info = decoded_line[13:].rstrip("\n").split(";")
            self._metadata[slicer_info[0]] = slicer_info[1].strip()
        elif self._plugin._metadata_slicer:
            if self._slicer == SLICER_PRUSA or self._slicer == SLICER_SUPERSLICER or self._slicer == SLICER_ORCA:
                if decoded_line[:2] == "; ":
                    re_result = self._metadata_regex.match(decoded_line.rstrip("\n"))
                    if re_result and len(re_result.groups()) == 2:
                        if re_result.groups()[0] != "SuperSlicer_config" and re_result.groups()[0] != "prusaslicer_config":
                            if len(re_result.groups()[1].strip()) < 50:
                                self._metadata[re_result.groups()[0]] = re_result.groups()[1].strip()
                            else:
                                self._logger.debug("Metadata line ignored because of it's length.")
            elif self._slicer == SLICER_SIMPLIFY3D:
                if decoded_line[:4] == ";   ":
                    re_result = self._metadata_regex.match(decoded_line.rstrip("\n"))
                    if re_result and len(re_result.groups()) == 2:
                        self._metadata[re_result.groups()[0]] = re_result.groups()[1].strip()                


            
class SlicerEstimatorFiledata(octoprint.filemanager.util.LineProcessorStream):
    def __init__(self, path, file_object, plugin):
        super().__init__(file_object.stream())
        self._logger = logging.getLogger("octoprint.plugins.SlicerEstimator")
        self.path = path
        self._file_object = file_object
        if hasattr(self._file_object, "path"):
            self.slicer = SlicerEstimatorMetadataFiles.detect_slicer(self._file_object.path)
        self._set_slicer_metadata()
        self.printtime = -1.0
        self._line_cnt = 0
        self._bytes_processed = 0
        self._time_list = list()
        self._change_list = list()   # format GCODE, Time, Progress in file
        self._plugin = plugin
        self._metadata_obj = SlicerEstimatorMetadata("local", self.path, self.slicer, self._plugin)


    # # get metadata from line
    # def process_metadata_line(self, decoded_line)
    #     # standard format for slicers
    #     # Cura: no standard format for metadata
    #     # Prusa/SuperSlicer: ; bridge_angle = 0
    #     # Simplify3D: ;   layerHeight,0.2
    #     if decoded_line[:13] == ";Slicer info:":
    #         slicer_info = decoded_line[13:].rstrip("\n").split(";")
    #         self._metadata[slicer_info[0]] = slicer_info[1].strip()
    #     elif self._plugin._metadata_slicer:
    #         if self.slicer == SLICER_PRUSA or self.slicer == SLICER_SUPERSLICER:
    #             if decoded_line[:2] == "; ":
    #                 re_result = self._metadata_regex.match(decoded_line.rstrip("\n"))
    #                 if re_result and len(re_result.groups()) == 2:
    #                     if re_result.groups()[0] != "SuperSlicer_config" and re_result.groups()[0] != "prusaslicer_config":
    #                         self._metadata[re_result.groups()[0]] = re_result.groups()[1].strip()
    #         elif self.slicer == SLICER_SIMPLIFY3D:
    #             if decoded_line[:4] == ";   ":
    #                 re_result = self._metadata_regex.match(decoded_line.rstrip("\n"))
    #                 if re_result and len(re_result.groups()) == 2:
    #                     self._metadata[re_result.groups()[0]] = re_result.groups()[1].strip()
        
    
    # Line parsing after upload  
    def process_line(self, line):
        self._line_cnt += 1
        self._bytes_processed += len(line)
        decoded_line = line.decode()
        if decoded_line[:10] == "@TIME_LEFT":
            return None
        elif decoded_line[:4] == "M600":                        
            if self._time_list:
                self._change_list.append(["M600", self._time_list[-1][1],self._line_cnt, self._bytes_processed])
            else:
                self._change_list.append(["M600", None, self._line_cnt, self._bytes_processed])
        elif decoded_line[:1] == "T":
            # Tool change
            if self._time_list:
                self._change_list.append([decoded_line[:2], self._time_list[-1][1], self._line_cnt, self._bytes_processed])
            else:
                self._change_list.append([decoded_line[:2], None, self._line_cnt, self._bytes_processed])
        elif self.slicer == SLICER_CURA:
            if decoded_line[:6] == ";TIME:":
                self.printtime = float(line[6:])
            if decoded_line[:13] == ";TIME_ELAPSED":
                self._time_list.append([self._line_cnt, self.printtime - float(decoded_line[14:])])               
                return(("@TIME_LEFT " + str(self.printtime - float(decoded_line[14:])) + "\r\n").encode() + line)
        elif self.slicer == SLICER_PRUSA or self.slicer == SLICER_SUPERSLICER or self.slicer == SLICER_ORCA:
            if decoded_line[:4] == "M73 ":
                re_result = self._regex.match(decoded_line)
                if re_result:
                    # first remaining time is the overall printtime
                    if self.printtime == -1.0:
                        self.printtime = float(re_result[2])*60
                    self._time_list.append([self._line_cnt, float(re_result[2])*60])
                    return(("@TIME_LEFT " + str(float(re_result[2])*60) + "\r\n").encode() + line)
        elif self.slicer == SLICER_SIMPLIFY3D:
            re_result = self._regex.match(decoded_line)
            if re_result:
                self.printtime = int(re_result[1])*60*60+int(re_result[2])*60

        if decoded_line[:1] == ";":
            # check a comment line for metadata
            self._metadata_obj.process_metadata_line(decoded_line)
            
        return line    


#    # slicer auto selection
    def _set_slicer_metadata(self):
        if self.slicer == SLICER_CURA:
            self._logger.info("Detected Cura")
        elif self.slicer == SLICER_PRUSA:
            self._logger.info("Detected PrusaSlicer")
            self._regex = re.compile("M73 P([0-9]+) R([0-9]+).*")
        elif self.slicer == SLICER_SUPERSLICER:
            self._logger.info("Detected SuperSlicer")
            self._regex = re.compile("M73 P([0-9]+) R([0-9]+).*")
        elif self.slicer == SLICER_SIMPLIFY3D:
            self._logger.info("Detected Simplify3D")
            self._regex = re.compile(";   Build [tT]ime: ([0-9]+) hours? ([0-9]+) minutes?")
        elif self.slicer == SLICER_ORCA:
            self._logger.info("Detected OrcaSlicer")
            self._regex = re.compile("M73 P([0-9]+) R([0-9]+).*")
        else:
            self._logger.warning("Autoselection of slicer not successful!")


    # Save gathered information to OctoPrint file metadata
    def store_metadata(self):
        # self._plugin._file_manager._storage_managers["local"].set_additional_metadata(self.path, "slicer_metadata", self._metadata, overwrite=True)
        # self._logger.debug(self._plugin._file_manager._storage_managers["local"].get_additional_metadata(self.path,"slicer_metadata"))    
        self._metadata_obj.store_metadata()    
        self._plugin._file_manager._storage_managers["local"].set_additional_metadata(self.path, "slicer_filament_change", self._change_list, overwrite=True)
        self._logger.debug(self._plugin._file_manager._storage_managers["local"].get_additional_metadata(self.path,"slicer_filament_change"))
        
        if self.slicer:
            if self.printtime == -1.0:
                self._plugin._sendNotificationToClient("no_timecodes_found")
            else:
                slicer_additional = dict()
                slicer_additional["printtime"] = self.printtime
                slicer_additional["lines"] = self._line_cnt
                slicer_additional["bytes"] = self._bytes_processed
                slicer_additional["slicer"] = self.slicer
                self._plugin._file_manager._storage_managers["local"].set_additional_metadata(self.path, "slicer_additional", slicer_additional, overwrite=True)
                self._logger.debug(self._plugin._file_manager._storage_managers["local"].get_additional_metadata(self.path,"slicer_additional"))
        else:
            self._logger.debug("No slicer additional informations found in GCODE: {}".format(self.path))

            
            
class SlicerEstimatorFilamentChange:
    def __init__(self, slicer_gcode, origin, path, file_manager):
        self._slicer_gcode = slicer_gcode
        self._origin = origin
        self.path = path
        self._regexStr = "^(M600 |T[0-9]|" + self._slicer_gcode + " )"
        self._compiled = re.compile(self._regexStr)
        self._command_arr = []
        self._return_arr = []
      
      
    def add_gcode(self, line):
        if self._compiled.match(line):
            self._command_arr.append(line)


    # scan for filament changes
    def search_filament_changes(self):
        change_list = list(filter(lambda p: p[1][:4] == "M600" or p[1][:1] == "T", self._command_arr))
        time_list = list(filter(lambda p: p[1][:len(self._slicer_gcode)] == self._slicer_gcode and self._plugin._parseEstimation(p[1]), self._command_arr))
        self._return_arr = []

        if len(change_list) > 0 and len(time_list) > 0:
            for change in change_list:
                time_line = min(time_list, key=lambda x:abs(x[0]-change[0]))
                self._logger.debug("Slicer-Comment {} found for filament change.".format(time_line[1]))
                slicer_estimation = [change[1].split()[0], self._plugin._parseEstimation(time_line[1])]
                self._return_arr.append(slicer_estimation)            
        
    
    def update_metadata(self):
        self._file_manager._storage_managers[self._origin].set_additional_metadata(self._path, "slicer_filament_change", self._return_arr, overwrite=True)
        self._logger.debug(self._file_manager._storage_managers[self._origin].get_additional_metadata(self._path,"slicer_filament_change"))


    def load_file(self):
        self._command_arr = SlicerEstimatorFileHandling.search_in_file_regex(self._file_manager.path_on_disk(self._origin, self._path), self._regexStr, 0, True)


from ast import Constant
import re
import logging
import octoprint.filemanager
import octoprint.filemanager.storage
import octoprint.filemanager.util


from .const import *
from .util import *



class SlicerEstimatorMetadata:
    def __init__(self, origin, path, file_manager):        
        self._origin = origin
        self._path = path
        self._file_manager = file_manager
        
        
    # search for material data
    def update_metadata(self):
        filament = SlicerEstimatorMetadata.find_metadata(self._file_manager.path_on_disk(self._origin, self._path))
        self._file_manager._storage_managers[self._origin].set_additional_metadata(self._path, "slicer", filament, overwrite=True)
        self._logger.debug(self._file_manager._storage_managers[self._origin].get_additional_metadata(self._path,"slicer"))


    def find_metadata(path_on_disk):
        # Format: ;Slicer info:<key>;<Displayname>;<Value>
        results = SlicerEstimatorFileHandling.search_in_file_start_all(path_on_disk, ";Slicer info:", 5000)
        if results is not None:
            filament = dict()
            for result in results:
                slicer_info = result[13:].rstrip("\n").split(";")
                if len(slicer_info) == 3:
                    # old format
                    filament[slicer_info[0]] = slicer_info[2].strip()
                else:
                    filament[slicer_info[0]] = slicer_info[1].strip()
            return filament


    # Update all metadata in files
    def update_metadata_in_files(file_manager):
        results =  file_manager._storage_managers["local"].list_files(recursive=True)
        filelist = dict()
        if results is not None:
            for resultKey in results:
                if results[resultKey]["type"] == "machinecode":
                    filelist[results[resultKey]["path"]] =  results[resultKey]
                if results[resultKey]["type"] == "folder":
                    SlicerEstimatorFileHandling.flatten_files(results[resultKey], filelist)
            for path in filelist:
                file_manager._storage_managers["local"].remove_additional_metadata(path, "slicer")
                metadata = SlicerEstimatorMetadata("local", path, file_manager)
                metadata.update_metadata()


            
class SlicerEstimatorFiledata(octoprint.filemanager.util.LineProcessorStream):
    def __init__(self, path, file_object, file_manager):
        super().__init__(file_object.stream())
        self._logger = logging.getLogger("octoprint.plugins.SlicerEstimator")
        self.path = path
        self._file_object = file_object
        self.slicer = self._detect_slicer()
        self.printtime = 0.0
        self._line_cnt = 0
        self._time_list = list()
        self._change_list = list()   # format GCODE, Time, Progress in file
        self._filament = dict()
        self._file_manager = file_manager

    
    # Line parsing after upload  
    def process_line(self, line):
        self._line_cnt += 1
        decoded_line = line.decode()
        if decoded_line[:10] == "@TIME_LEFT":
            return None
        elif decoded_line[:4] == "M600":                        
            if self._time_list:
                self._change_list.append(["M600", self._time_list[-1][1],self._line_cnt])
            else:
                self._change_list.append(["M600", 0.0, 1])
        elif decoded_line[:1] == "T" and len(decoded_line) == 2:
            # Tool change
            if self._time_list:
                self._change_list.append([decoded_line, self._time_list[-1][1], self._line_cnt])
            else:
                self._change_list.append([decoded_line, 0.0, 1])
        elif decoded_line[:13] == ";Slicer info:":
                slicer_info = decoded_line[13:].rstrip("\n").split(";")
                if len(slicer_info) == 3:
                    # old format
                    self._filament[slicer_info[0]] = slicer_info[2].strip()
                else:
                    self._filament[slicer_info[0]] = slicer_info[1].strip()
        elif self.slicer == SLICER_CURA:
            if decoded_line[:6] == ";TIME:":
                self.printtime = float(line[6:])
            if decoded_line[:13] == ";TIME_ELAPSED":
                self._time_list.append([self._line_cnt, self.printtime - float(decoded_line[14:])])               
                return(("@TIME_LEFT " + str(self.printtime - float(decoded_line[14:])) + "\r\n").encode() + line)
        elif self.slicer == SLICER_PRUSA:
            if decoded_line[:4] == "M73 ":
                re_result = self._regex.match(decoded_line)
                if re_result:
                    if self.printtime == 0.0:
                        self.printtime = re_result[1]
                    else:
                        self._time_list.append(self._line_cnt, re_result[1])
        elif self.slicer == SLICER_SIMPLIFY3D:
            re_result = self._regex.match(decoded_line)
            if re_result:
                self.printtime = re_result[0]*60*60+re_result[1]*60
            
        return line    


   # slicer auto selection
    def _detect_slicer(self):
        line = SlicerEstimatorFileHandling.search_in_file_regex(self._file_object.path,".*(PrusaSlicer|Simplify3D|Cura_SteamEngine).*")
        if line:
            if  "Cura_SteamEngine" in line:
                self._logger.info("Detected Cura")
                return SLICER_CURA
            elif "PrusaSlicer" in line:
                self._logger.info("Detected PrusaSlicer")
                self._regex = re.compile("M73 P([0-9]+) R([0-9]+).*")
                return SLICER_PRUSA
            elif "Simplify3D" in line:
                self._logger.info("Detected Simplify3D")
                self._regex = re.compile(";   Build time: ([0-9]+) hours? ([0-9]+) minutes")
                return SLICER_SIMPLIFY3D
        else:
            self._logger.warning("Autoselection of slicer not successful!")


    #Save gathered information to OctoPrint file metadata
    def store_metadata(self):
        self._file_manager._storage_managers["local"].set_additional_metadata(self.path, "slicer", self._filament, overwrite=True)
        self._logger.debug(self._file_manager._storage_managers["local"].get_additional_metadata(self.path,"slicer"))        
        self._file_manager._storage_managers["local"].set_additional_metadata(self.path, "slicer_filament_change", self._change_list, overwrite=True)
        self._logger.debug(self._file_manager._storage_managers["local"].get_additional_metadata(self.path,"slicer_filament_change"))
        
        slicer_additional = dict()
        slicer_additional["printtime"] = self.printtime
        slicer_additional["slicer"] = self.slicer
        self._file_manager._storage_managers["local"].set_additional_metadata(self.path, "slicer_additional", slicer_additional, overwrite=True)
        self._logger.debug(self._file_manager._storage_managers["local"].get_additional_metadata(self.path,"slicer_additional"))

            
            
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


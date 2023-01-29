import re
import io

class SlicerEstimatorFileHandling:
    # generic file search with RegEx
    def search_in_file_regex(path_on_disk, pattern, maxrows = 0, multiple = False):                
        compiled = re.compile(pattern)
        rownumber = 0
        return_arr = []

        with io.open(path_on_disk, mode="r", encoding="utf8", errors="replace") as f:
            for line in f:
                rownumber += 1
                if compiled.match(line):
                    if multiple:
                       return_arr.append([rownumber, line])
                    else:
                        return line
                if maxrows != 0 and rownumber >= maxrows:
                    break
            if multiple:
                return return_arr


    # generic file search and find all occurences beginning with
    def search_in_file_start_all(path_on_disk, pattern, rows = 0):        
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
    
    
    def return_file_lines(path_on_disk, rows = 0):
        steps = rows
        return_arr = []

        with io.open(path_on_disk, mode="r", encoding="utf8", errors="replace") as f:
            for line in f:
                return_arr.append(line)
                if rows > 0:
                    steps -= 1
                    if steps <= 0:
                        return return_arr
        return return_arr
       
    
    
    # recursive function to flatten the filelist hierarchy - should be called with objectList only
    def flatten_files(objectList, filelist = dict(), level = 0):
        for objectKey in objectList:
            if objectList[objectKey]["type"] == "machinecode":
                filelist[objectList[objectKey]["path"]] = objectList[objectKey]
            elif objectList[objectKey]["type"] == "folder":
               SlicerEstimatorFileHandling.flatten_files(objectList[objectKey]["children"], filelist, level + 1)
        if level == 0:
            return filelist
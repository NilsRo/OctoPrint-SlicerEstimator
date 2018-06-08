Estimator for OctoPrint that uses data embedded in gcode by [gcodestat](https://github.com/arhi/gcodestat)
=====================================================================

## Requirement
 * Needs octoprint 1.3.9 that implements
   http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-filemanager-analysis-factory
   http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-printer-estimation-factory
 * Needs M117 codes in your G-Code to look like (12hours+43minutes+4seconds or 43minutes + 4seconds or 4 seconds):
     M117 35% Remaining ( 12:43:04 )
     M117 17% Remaining ( 43:04 )
     M117 5% Remaining ( 04 )
 * You can use [gcodestat](https://github.com/arhi/gcodestat) to pre-process your G-Code files and embed these M117 codes

## Issues
 * Does not know how to handle prints from the SD card, only knows how to handle prints from local octoprint storage. In case of SDCARD prints it will show fixed 9.5 days time to finish
 * Does not know how to handle files that do not have M117 codes embedded and till properly formatted M117 code is found it will report 9.5 days time to finish
 
## ToDo
 * Auto preprocess the G-Code file on upload and embed M117 codes (use externally gcodestat for e.g. for speed)
 * Allow original OctoPrint estimator to work in case we don't find M117 or in case of SDCARD prints
 
## Notes
 * I'm no Python developer, I do C++, so if you can suggest code cleanup, solving something differently etc. feel free to step in
 
 
 

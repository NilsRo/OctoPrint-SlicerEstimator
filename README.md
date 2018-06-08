# Estimator for OctoPrint that uses data embedded in gcode by [gcodestat](https://github.com/arhi/gcodestat)

## Requirement
 * Needs octoprint 1.3.9 that implements
   * http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-filemanager-analysis-factory
   * http://docs.octoprint.org/en/maintenance/plugins/hooks.html#octoprint-printer-estimation-factory
 * Needs M117 codes in your G-Code to look like (12hours+43minutes+4seconds or 43minutes + 4seconds or 4 seconds):
   * M117 35% Remaining ( 12:43:04 )
   * M117 17% Remaining ( 43:04 )
   * M117 5% Remaining ( 04 )
 * You can use [gcodestat](https://github.com/arhi/gcodestat) to pre-process your G-Code files and embed these M117 codes

## ToDo
 * Auto preprocess the G-Code file on upload and embed M117 codes (use externally gcodestat for e.g. for speed)
 * Push a % value to the OctoPrint (I have the value I just have no clue how to send it to OctoPrint)
 
## Notes
 * I'm no Python developer, I do C++, so if you can suggest code cleanup, solving something differently etc. feel free to step in
 * In case there are no M117 codes that can be recognised the original estimator from OctoPrint will be used
 * In case SDCARD print is used the original estimator from OctoPrint will be used
 
 
 

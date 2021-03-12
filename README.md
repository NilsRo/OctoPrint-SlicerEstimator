# Slicer Print Time Estimator is a generic implemenation to read remaining time to print embedded in the GCODE file by the slicer
With this plugin you can use the more accurate estimation of time remaining of the slicer instead of OctoPrints estimations. So it will be very accurate, as the slicer created each command of the GCODE. Thanks to arhi for the idea and first implementation.

The slicer is detected automatically, the default configurations supports the following slicers. Also you can add custom settings according your needs for other slicers or requirements. 

* Cura
* Cura M117
* Simplify3D
* PrusaSlicer


Slicer Print Time Estimator detected the embedded remaining time if there is a checkmark right of the estimation:

![](images/OctoPrint-estimator_dot.png)

Also the estimated time of an upload is updated if slicer comments are found. It is possible to deactivate this in the settings if perhaps another plugin is installed doing this.

![](images/file_metadata1.png)![](images/file_metadata2.png)

## Slicers supported

### Cura
With Cura native no changes has to be applied to Cura. The overall print time is read out of a comment in the GCODE. For a correct estimation OctoPrints percentage done is used as there is only the overall print time available.

### Cura M117
Remaining time is read out of M117 commands added by Cura if the Post-Processing actions are activated. The slicer will update the remaining print time continuously.
![](images/Cura.png)

### Simplify3D
With Simplify3D no changes has to be applied to Simplify3D. The overall print time is read out of a comment in the GCODE. For a correct estimation OctoPrints percentage done is used as there is only the overall print time available.

### PrusaSlicer
Remaining time is read out of M73 commands added by PrusaSlicer. The slicer will update the remaining print time continuously.

## Notes
 * If no slicer is detected the original estimator from OctoPrint will be used.
 * In case SDCARD print is used the original estimator from OctoPrint will be used
 * Compared to slicer estimations the average estimation by OctoPrint (based on the average of the last real prints) could be more accurate. So you can change the settings if you like to use average estimation if available. It is not available for new GCODE files.
 * GCODE files are scanned in background so until the necessary information is found the OctoPrint estimator is used. There is no delay in start printing but with files of e.g. 150Mbyte in size the scan could take some seconds.
 * If you like to see more details what happens in the background simply activate DEBUG mode in OctoPrint logging for the plugin. If you want open a ticket please attach the log there.
 * Be aware that other plugins could change the GCODE. This could interfere with Slicer Print Time Estimator if Cura M117 or PrusaSlicer is used. Both reads GCODEs that perhaps will be overwritten by e.g. an ETA plugin.

## Custom Settings
Example: For the following command "M117 100% Remaining 1 weeks 6 days ( 07:54:19 )" you can use RegEx "M117 .+ Remaining ([0-9]+) weeks.+" with Match 1 to get the weeks. To get the minutes you should use "M117 .+ Remaining .+\( ([0-9]+):([0-9]+):([0-9]+) \)" and Match 2 to avoid an issue if weeks are not shown. 

 
![](images/Gcode.png)

![](images/Settings_Custom.png)

I like to suggest regex101.com for testing and to get the right match group.

![](images/RegEx.png)

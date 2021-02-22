# Slicer Estimator is a generic implemenation to interpret M73 and M117 commands from slicer to set remaining time to print
With this plugin and active Post Processing in e.g. Cura you will get an exact estimation of time remaining as it will set from information analysed by the slicer. So it will be very accurate. Thanks to arhi for the idea and first implementation.

The default configuration matches the syntax of Cura, but you can change it in the plugin configuration according your needs.

Example: For the following command "M117 100% Remaining 1 weeks 6 days ( 07:54:19 )" you can use RegEx "M117 .+ Remaining ([0-9]+) weeks.+" with Match 1 to get the weeks. To get the minutes you should use "M117 .+ Remaining .+\( ([0-9]+):([0-9]+):([0-9]+) \)" and Match 2 to avoid an issue if weeks are not shown. 

![](images/Gcode.png)

![](images/Cura.png)

![](images/Settings_Basic.png)

![](images/Settings_Custom.png)

I like to suggest regex101.com for testing and to get the right match group.

![](images/RegEx.png)

## Requirement
 * Needs M73 and M117 codes in your GCODE. As percentage done is not processed further it is not really necessary.
 * You have to add Cura Post Processing Script "Display Progress On LCD" and activate "Time Remaining" to add necessary information to GCODE file. 
## Notes
 * In case there are no matching M73 or M117 codes the original estimator from OctoPrint will be used
 * In case SDCARD print is used the original estimator from OctoPrint will be used
 * For known slicers only the slicer has to be selected and the slicers Post Processing has to be set. If no corresponding commands are found standard estimation is used.
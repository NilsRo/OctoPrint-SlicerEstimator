# M117 Estimator is general way to interpret M117 commands from slicer to set remaining time to print
With this plugin and active Post Processing in e.g. Cura you will get an exact estimation of time remaining as it will set from information analysed in the slicer. So it will be very accurate. Thanks to arhi for the idea and first implementation.

The default configuration matches the syntax of Cura, but you can change it in the plugin configuration according your needs.

Example: For the following command "M117 100% Remaining 1 weeks 6 days ( 07:54:19 )" you can use RegEx "M117 .+ Remaining ([0-9]+) weeks.+" with Match 1 to get the weeks. To get the minutes you should use "M117 .+ Remaining .+\( ([0-9]+):([0-9]+):([0-9]+) \)" and Match 2 to avoid an issue if weeks are not shown. 

![](images/Gcode.png)

![](images/Cura.png)

![](images/Settings.png)

I like to suggest regex101.com for testing and to get the right match group.

![](images/RegEx.png)

## Requirement
 * Needs M73 and M117 codes in your G-Code in Cura format. M73 contains percentage done and M117 remaining time. As percentage done is not processed further it is not really necessary.
 * You have to add Cura Post Processing Script "Display Progress On LCD" and activate "Time Remaining" and "Percentage" to add necessary information to G-Code file. 
## Notes
 * In case there are no M117 codes that can be recognised the original estimator from OctoPrint will be used
 * In case SDCARD print is used the original estimator from OctoPrint will be used
 * The Plugin does not have anything to configure simply install and activate Post Processing. If no corresponding commands are found standard estimation is used.


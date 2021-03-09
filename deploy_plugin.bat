robocopy %1 %2 /MIR /Z /W:1 /R:1
rem // Terminate the script in case `robocopy` failed:
if ErrorLevel 8 exit /B 1
rem // Here we land when case `robocopy` succeeded;
rem // Finally explicitly force a zero exit code:
exit /B 0
ECHO OFF
ECHO Back-up of values
xcopy /y C:\Users\davidlio\source\nig\node1\src\common\values.py C:\Users\davidlio\source\nig\values_temp\node1
xcopy /y C:\Users\davidlio\source\nig\node2\src\common\values.py C:\Users\davidlio\source\nig\values_temp\node2
PAUSE
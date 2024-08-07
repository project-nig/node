ECHO OFF
ECHO Back-up of values
xcopy /y C:\....path to source folder...\nig\node1\src\common\values.py C:\....path to source folder...\nig\values_temp\node1
xcopy /y C:\....path to source folder...\nig\node2\src\common\values.py C:\....path to source folder...\nig\values_temp\node2
PAUSE
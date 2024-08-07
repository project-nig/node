ECHO OFF
ECHO Back-up of values
xcopy /y ....path to source folder...\nig\node1\src\common\values.py ....path to source folder...\nig\values_temp\node1
xcopy /y ....path to source folder...\nig\node2\src\common\values.py ....path to source folder...\nig\values_temp\node2
PAUSE
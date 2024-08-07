ECHO OFF
ECHO Replication of environment
break>C:\....path to source folder...\nig\node3\files\BLOCKCHAIN_DIR.txt
break>C:\....path to source folder...\nig\node3\files\MEMPOOL_DIR.txt
break>C:\....path to source folder...\nig\node3\files\LEADER_NODE_SCHEDULE_DIR.txt
break>C:\....path to source folder...\nig\node3\files\KNOWN_NODES_DIR.txt
break>C:\....path to source folder...\nig\node3\files\MASTER_STATE_DIR.txt
rmdir /s /q "C:\....path to source folder...\nig\node1\STORAGE\"
MD "C:\....path to source folder...\nig\node1\STORAGE\"
rmdir /s /q "C:\....path to source folder...\nig\node2\STORAGE\"
MD "C:\....path to source folder...\nig\node2\STORAGE\"
rmdir /s /q "C:\....path to source folder...\nig\node3\STORAGE\"
MD "C:\....path to source folder...\nig\node3\STORAGE\"
rmdir /S /q "C:\....path to source folder...\nig\node1\src\"
rmdir /S /q "C:\....path to source folder...\nig\node2\src\"
xcopy /s /y  C:\....path to source folder...\nig\node3\src\ C:\....path to source folder...\nig\node2\src\
xcopy /s /y C:\....path to source folder...\nig\node3\src\ C:\....path to source folder...\nig\node1\src\
xcopy /s /y C:\....path to source folder...\nig\node3\files\ C:\....path to source folder...\nig\node2\files\
xcopy /s /y C:\....path to source folder...\nig\node3\files\ C:\....path to source folder...\nig\node1\files\
xcopy /s /y C:\....path to source folder...\nig\values_temp\node1\ C:\....path to source folder...\nig\node1\src\common\
xcopy /s /y C:\....path to source folder...\nig\values_temp\node2\ C:\....path to source folder...\nig\node2\src\common\
PAUSE
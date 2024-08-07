ECHO OFF
ECHO Replication of environment
break>C:\Users\davidlio\source\nig\node3\files\BLOCKCHAIN_DIR.txt
break>C:\Users\davidlio\source\nig\node3\files\MEMPOOL_DIR.txt
break>C:\Users\davidlio\source\nig\node3\files\LEADER_NODE_SCHEDULE_DIR.txt
break>C:\Users\davidlio\source\nig\node3\files\KNOWN_NODES_DIR.txt
break>C:\Users\davidlio\source\nig\node3\files\MASTER_STATE_DIR.txt
rmdir /s /q "C:\Users\davidlio\source\nig\node1\STORAGE\"
MD "C:\Users\davidlio\source\nig\node1\STORAGE\"
rmdir /s /q "C:\Users\davidlio\source\nig\node2\STORAGE\"
MD "C:\Users\davidlio\source\nig\node2\STORAGE\"
rmdir /s /q "C:\Users\davidlio\source\nig\node3\STORAGE\"
MD "C:\Users\davidlio\source\nig\node3\STORAGE\"
rmdir /S /q "C:\Users\davidlio\source\nig\node1\src\"
rmdir /S /q "C:\Users\davidlio\source\nig\node2\src\"
xcopy /s /y  C:\Users\davidlio\source\nig\node3\src\ C:\Users\davidlio\source\nig\node2\src\
xcopy /s /y C:\Users\davidlio\source\nig\node3\src\ C:\Users\davidlio\source\nig\node1\src\
xcopy /s /y C:\Users\davidlio\source\nig\node3\files\ C:\Users\davidlio\source\nig\node2\files\
xcopy /s /y C:\Users\davidlio\source\nig\node3\files\ C:\Users\davidlio\source\nig\node1\files\
PAUSE
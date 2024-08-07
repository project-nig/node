ECHO OFF
ECHO Replication of environment
break>....path to source folder...\node3\files\BLOCKCHAIN_DIR.txt
break>....path to source folder...\node3\files\MEMPOOL_DIR.txt
break>....path to source folder...\node3\files\LEADER_NODE_SCHEDULE_DIR.txt
break>....path to source folder...\node3\files\KNOWN_NODES_DIR.txt
break>....path to source folder...\node3\files\MASTER_STATE_DIR.txt
rmdir /s /q "....path to source folder...\node1\STORAGE\"
MD "....path to source folder...\node1\STORAGE\"
rmdir /s /q "....path to source folder...\node2\STORAGE\"
MD "....path to source folder...\node2\STORAGE\"
rmdir /s /q "....path to source folder...\node3\STORAGE\"
MD "....path to source folder...\node3\STORAGE\"
rmdir /S /q "....path to source folder...\node1\src\"
rmdir /S /q "....path to source folder...\node2\src\"
xcopy /s /y  ....path to source folder...\node3\src\ ....path to source folder...\node2\src\
xcopy /s /y ....path to source folder...\node3\src\ ....path to source folder...\node1\src\
xcopy /s /y ....path to source folder...\node3\files\ ....path to source folder...\node2\files\
xcopy /s /y ....path to source folder...\node3\files\ ....path to source folder...\node1\files\
PAUSE
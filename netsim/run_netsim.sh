#!/bin/bash
##### Wrapper shell script for netsim.py

if [ "$2" == "start" ]; then
	### Stop netsim components if they're running
	sudo ./netsim.py "$1" checkstopnetsim 
	### Build click configuration
	sudo ./netsim.py "$1" buildclick 
	### This needs to be called in a shell process
	### If you call it in a Python process, it will die when the Python process dies
	echo "Starting click"
	sudo /usr/local/bin/click autogen.click &>/dev/null &
	sleep 1
fi
echo "Running netsim command, output in netsimlogout.txt"
sudo ./netsim.py "$@" &>netsimlogout.txt

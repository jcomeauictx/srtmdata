#!/bin/bash
# strip out all unnecessary characters to avoid backdoor shells
request=$DOCUMENT_ROOT${REQUEST_URI//[^0-9A-Za-z/_.-]/}
logger received request for $request
if [ -e $request.zip ]; then
	logger serving $request from $request.zip
	printf "Status: 203 Generated from zipfile\r\n"
	printf "Content-type: application/octet-stream\r\n"
	printf "\r\n"
	unzip -p $request.zip $(basename $request)
else
	logger resending 404 status
	printf "Status: 404 File not found\r\n"
	printf "Content-type: text/plain\r\n"
	printf "\r\n"
	echo 404 File $request not found
	env
fi

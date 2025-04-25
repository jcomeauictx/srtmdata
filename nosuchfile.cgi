#!/bin/bash
# strip out all unnecessary characters to avoid backdoor shells
request=$DOCUMENT_ROOT${REDIRECT_QUERY_STRING//[^0-9A-Za-z/_.-]/}
logger received request for $request
if [ -e $request.zip ]; then
	logger serving $request from $request.zip
	printf "Status: 203 Generated from zipfile\r\n"
	printf "Content-type: application/octet-stream\r\n"
	printf "\r\n"
	unzip -p $request.zip $(basename $request)
else
	printf "Content-type: text/html\r\n\r\n"
	echo 404 File Not Found
fi

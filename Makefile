SHELL := /bin/bash
OPT := -OO # use `make OPT=-OO` for speed, no debugging output
PYTHON := python3 $(OPT)
STORAGE ?= /usr/local/share/gis/srtm
DRYRUN ?= --dry-run
SRTM_PATTERN := .*_3arc_
export SRTM_PATTERN
all: srtm.pylint make.log
make.log: .FORCE | srtm.py
	set -euxo pipefail; \
	{ $(PYTHON) $| 2>&1 1>&3 3>&- | tee $(@:.log=.err); } \
	 3>&1 1>&2 | tee $@
upload:
	for host in srtm1 srtm2; do \
	 cd $(STORAGE) && rsync -avuz $(DRYRUN) . $$host:$(STORAGE)/; \
	done
%.pylint: %.py
	pylint $<
server:
	# modifications to $STORAGE on server
	# empty index.html files prevent listing directories without
	# needing Apache directives.
	# compressing saves space on server, and .htaccess can be used
	# to decompress on the fly.
	# must `make server` *after* $STORAGE fully populated for foolproof
	# operation.
	for directory in $(STORAGE)/srtm? $(STORAGE)/srtm?/???; do \
	 touch $$directory/index.html; \
	done
.PRECIOUS: make.log
.FORCE:

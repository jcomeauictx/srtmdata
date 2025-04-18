SHELL := /bin/bash
OPT := # use `-OO` for speed, no debugging output
PYTHON := python3 $(OPT)
make.log make.err: .FORCE | download.py
	set -euxo pipefail; \
	{ $(PYTHON) $| 2>&1 1>&3 3>&- | tee $(@:.log=.err); } \
	 3>&1 1>&2 | tee $@
%.bil: %_bil.zip
	unzip -o $<
# rename e.g. n00_e000_3arc_v2.bil to /usr/local/share/gis/hgt/N00E000.hgt
move:
	for filename in *.bil; do \
	 renamed=$(echo $filename | tr -d _ | tr nsew NSEW | cut -c1-7).hgt; \
	 mv -f $filename /usr/local/share/gis/hgt/$renamed; \
	done
.PRECIOUS: download.log
.FORCE:

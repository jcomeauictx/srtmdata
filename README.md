Not that many years ago, it was possible to download SRTM3 data easily from
a USGS website, <https://dds.cr.usgs.gov/srtm/version2_1/SRTM3>, but that
page now returns a 404 error. The data is available at
<https://earthexplorer.usgs.gov/>, but hidden behind layer upon layer of
webapp foolishness. This project will be an attempt to illuminate the steps
necessary, and perhaps automate some or all of it.

## Quickstart

tl;dr: just keep running `make`, taking note of where it fails and fixing the
problem, until you have all the SRTM3 data.

less quick but more deterministic:

* sign up for an account at earthexplorer.usgs.gov
* add your login credentials to your $HOME/.netrc file
* create the directories you will need for temporary and permanent storage
  of SRTM data; see the Makefile and srtm.py
* running `make` or `./srtm.py` without args will first attempt to decompress
  any existing downloaded SRTM zipfiles and place the resulting HGT files into
  permanent storage;
* failing that, will attempt to initiate download of any SRTM data already
  added to cart;
* failing that, will loop through all 14000+ SRTM quadrants and add them
  to the cart.
* a minimum of 3 runs is necessary to complete all the steps.

## Developer's notes
* ["Unable to obtain working Selenium manager binary" using Debian selenium](https://forums.linuxmint.com/viewtopic.php?t=435499), [answer](https://stackoverflow.com/a/78940456/493161)

# AB3GY pyWsjtxHighlight
Amateur radio application to control custom background color highlighting of WSJT-X decoded messages.

Callsigns logged today are highlighted in red.  Callsigns logged within the last N days are highlighted in orange. Used primarily to help me remember which POTA/SOTA stations I've recently hunted, and which ones I can call again.

Communicates with WSJT-X using a UDP socket connection.

See the `print_usage()` function for some more information.

Developed for personal use by the author, but available to anyone under the license terms below.


## Dependencies
Written for Python 3.x. 

Requires the following packages developed by me:
* ab3gy-adif: https://github.com/tkerr/ab3gy-adif
* ab3gy-wsjtx: https://github.com/tkerr/ab3gy-wsjtx

Copy these packages to a local directory and modify the `_env_init.py` file to point to the packages.  No support for `pip install` etc. is provided at this time.

Currently only works on Windows operating systems.  Makes use of the `%LOCALAPPDATA%` environment variable to access the WSJT-X log file.

## Author
Tom Kerr AB3GY
ab3gy@arrl.net

## License
Released under the 3-clause BSD license.
See license.txt for details.

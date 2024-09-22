###############################################################################
# pyWsjtxHighlight.py
# Author: Tom Kerr AB3GY
#
# Amateur radio application to control custom background color highlighting 
# of WSJT-X decoded messages.
#
# Currently only works on Windows systems.
#
# Designed for personal use by the author, but available to anyone under the
# license terms below.
###############################################################################

###############################################################################
# License
# Copyright (c) 2023 Tom Kerr AB3GY (ab3gy@arrl.net).
#
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice,   
# this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,  
# this list of conditions and the following disclaimer in the documentation 
# and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without 
# specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE 
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
###############################################################################

# System level packages.
from datetime import datetime, timezone
import getopt
import os
import re
import sys

# Local environment init.
import _env_init

# Local packages.
from adif import adif, freq2band
from adif_iter import adif_iter
from wsjtxmon import wsjtxmon
from QColor import QColor


##############################################################################
# Globals.
##############################################################################
localappdata = os.getenv('LOCALAPPDATA')
scriptname = os.path.basename(sys.argv[0])
scriptdir = os.path.split(sys.argv[0])[0]
wsjtx_band = ''
wsjtx_mode = ''
year_now = 0
leap_now = 0
julian_now = 0
num_days = 7
verbose = False

# Regular expression for all amateur radio callsigns.
# Assumes everything is uppercase.
callsign_re = re.compile("[A-Z0-9]{1,3}[0-9][A-Z0-9]{0,3}[A-Z]")


##############################################################################
# Functions.
############################################################################## 

def print_usage():
    """
    Print a usage statement and exit.
    """
    global scriptname
    global num_days
    print('Usage: ' + scriptname + ' [-abBhlnptv]')
    print('Manage custom color highlighting of WSJT-X decoded messages.')
    print('Callsigns logged today are highlighted in red.')
    print('Callsigns logged within the last N days are highlighted in orange (default = {}).'.format(num_days))
    print('Still under development.')
    print('Options:')
    print('  -a addr = Set WSJT-X UDP server IP address')
    print('  -b = Build the application database from the WSJT-X ADIF log if it is older')
    print('  -B = Always build the application database from the WSJT-X ADIF log')
    print('  -h = Print this message and exit')
    print('  -l log = Use this WSJT-X ADIF log file')
    print('  -n days = Set the number of days for orange highlighting')
    print('  -p port = Set WSJT-X UDP server port')
    print('  -t sec = Set server timeout seconds')
    print('  -v = Enable verbose printing')
    sys.exit(1)

# ----------------------------------------------------------------------------
def leap_year(year):
    """
    Return 1 if year is a leap year, or 0 otherwise.
    """
    leap = 0
    if year % 400 == 0:   # Some centuries are leap years...
        leap = 1
    elif year % 100 == 0: # ... but most are not ...
        leap = 0
    elif year % 4 == 0:   # ... even though other divisibly-by-four years are
        leap = 1
    return leap

# ----------------------------------------------------------------------------
def parse_date(qso_date):
    """
    Parse the QSO date string and return the integer year, leap year flag,
    and julian date.
    """
    year = int(qso_date[0:4])
    month = int(qso_date[4:6])
    day = int(qso_date[6:8])
    df = datetime(year, month, day)
    julian = int(df.strftime('%j'))
    return (year, leap_year(year), julian)    

# ----------------------------------------------------------------------------
def build_database(app_database_file, wsjtx_adif_file):
    """
    Build the application database from the WSJT-X ADIF log.
    """
    global verbose
    qso_count = 0
    db_list = []
    db = open(app_database_file, 'w')
    adif_log = adif_iter(wsjtx_adif_file)
    for qso in adif_log.all_qsos():
        qso_count += 1
        myAdif = adif(qso)
        call = myAdif.get_field('CALL').upper()
        mode = myAdif.get_field('MODE').upper()
        band = myAdif.get_field('BAND').upper()
        qso_date = myAdif.get_field('QSO_DATE')
        (year, leap, julian) = parse_date(qso_date)
        db_entry = '{},{},{},{},{},{}\n'.format(call, mode, band, year, leap, julian)
        db_list.append(db_entry)
    db_list.sort()
    for db_entry in db_list:
        db.write(db_entry)
    db.write('ZZZZZZ,NONE,NONE,2001,0,1\n') # Insert a bogus record at the end
    db.close()
    if verbose: print('Database QSO count: {}'.format(qso_count))

# ------------------------------------------------------------------------
def get_callsign(msg):
    """
    Return the callsign from a decoded message string.
    """
    global callsign_re
    global verbose
    callsign = ''
    msg_s = msg.split()
    for txt in msg_s[1:]:  # Skip the first text, it is either CQ or DX call
        if callsign_re.match(txt):
            callsign = txt
            break
    return callsign

# ----------------------------------------------------------------------------
def binary_search(call, db):
    """
    Get the index of the callsign in the database using a binary search.
    Return -1 if not found.
    """
    global verbose
    low = 0
    mid = 0
    high = len(db) - 1
    
    while (low <= high):
        mid = (high + low) // 2
        ref = db[mid].split(',')[0]
        
        # If call is greater, ignore left half.
        if (ref < call):
            low = mid + 1
            
        # If call is smaller, ignore right half.
        elif (ref > call):
            high = mid - 1
        
        # Found call.
        else:
            return mid
            
    # Not found.
    return -1

# ----------------------------------------------------------------------------
def call_index(call, db):
    """
    Get the index of the first occurrence of the callsign in the database.
    Return -1 if not found.
    """
    global verbose
    
    # Use binary search to find the call in the database.
    index = binary_search(call, db)
    
    # Back up to the first occurrence of the call.
    while index > 0:
        prev = db[index-1].split(',')[0]
        if (prev == call):
            index -= 1
        else:
            break
    return index

# ----------------------------------------------------------------------------
def highlight_level(call, index, db):
    """
    Determine the highlight level of a callsign in a decoded message.
    """
    global year_now
    global leap_now
    global julian_now
    global num_days
    global verbose
    
    level = 0 # 0 = do not highlight, 1 = orange, 2 = red
    db_entry = db[index].strip().split(',')
    while (call == db_entry[0]):
        if (db_entry[1] == wsjtx_mode) and (db_entry[2] == wsjtx_band):
            # Mode and band match.
            #print(db_entry)
            year_qso = int(db_entry[3])
            julian_qso = int(db_entry[5])
            
            if (year_now == year_qso):
                delta = julian_now - julian_qso
                if (delta == 0):
                    # Log entry is today.
                    level = 2
                    if verbose: print('{} logged today'.format(call))
                    break
                elif (delta < num_days):
                    # Log entry was less than num_days ago.
                    if (level == 0): 
                        level = 1
                        if verbose: 
                            if (delta == 1):
                                print('{} logged 1 day ago'.format(call))
                            else:
                                print('{} logged {} days ago'.format(call, delta))
                        
            elif (year_now - year_qso == 1):
                # Special case of year rollover.
                leap_qso = int(db_entry[4])
                delta = (julian_now + leap_qso + 365) - julian_qso
                if (delta < num_days):
                    # Log entry was less than num_days ago.
                    if (level == 0): 
                        level = 1
                        if verbose: 
                            if (delta == 1):
                                print('{} logged 1 day ago'.format(call))
                            else:
                                print('{} logged {} days ago'.format(call, delta))
        index += 1
        db_entry = db[index].strip().split(',')
    return level

# ----------------------------------------------------------------------------
def parse_decode(message, db):
    """
    Parse a WSJT-X decode message and return its callsign and highlight level.
    """
    global verbose
    level = 0
    msg_str = message[8]
    call = get_callsign(msg_str)
    
    # Limit highlighting to CQ messages.
    if msg_str.startswith('CQ') and (len(call) > 0):
        index = call_index(call, db)
        if index >= 0:
            #print('{} found at index {}'.format(call, index))
            level = highlight_level(call, index, db)
    return (call, level)

# ----------------------------------------------------------------------------
def parse_status(message):
    """
    Parse a WSJT-X status message.
    """
    global wsjtx_band
    global wsjtx_mode
    global verbose
    freq = float(message[2]) * 0.000001
    wsjtx_band = freq2band(freq).upper()
    wsjtx_mode = message[3].upper()


##############################################################################
# Main program.
############################################################################## 
if __name__ == "__main__":
    
    udp_ip   = '127.0.0.1'
    udp_port = 2237
    timeout  = 16
    build_database_flag = 0 # 0 = don't build, 1 = build if older, 2 = always build
    logged_count = 0
    
    wsjtx_adif_file = os.path.join(localappdata, 'WSJT-X', 'wsjtx_log.adi')
    app_database_file = os.path.join(scriptdir, 'logdata.csv')
    
    # Get command line options.
    # See print_usage() for details.
    try:
        (opts, args) = getopt.getopt(sys.argv[1:], 'a:bBhl:n:p:t:v')
    except (getopt.GetoptError) as err:
        print(str(err))
        sys.exit(1)
    for (o, a) in opts:
        if (o == '-a'):
            udp_ip = str(a)
        elif (o == '-b'):
            build_database_flag = 1
        elif (o == '-B'):
            build_database_flag = 2
        elif (o == '-h'):
            print_usage()
        elif (o == '-l'):
            wsjtx_adif_file = str(a)
        elif (o == '-n'):
            num_days = int(a)
            if (num_days < 2):
                print('Option -n value must be greater than 1.')
                sys.exit(1)
        elif (o == '-p'):
            udp_port = int(a)
        elif (o == '-t'):
            timeout = int(a)
        elif (o == '-v'):
            verbose = True
    
    # Initialize the application database.
    if not os.path.isfile(app_database_file):
        if verbose:
            print('Application database does not exist, creating it')
        build_database(app_database_file, wsjtx_adif_file)
    elif build_database_flag == 2:
        if verbose:
            print('Building application database')
        build_database(app_database_file, wsjtx_adif_file)
    elif build_database_flag == 1:
        app_mod_time = os.path.getmtime(app_database_file)
        wsjtx_log_time = os.path.getmtime(wsjtx_adif_file)
        if app_mod_time < wsjtx_log_time:
            if verbose:
                print('Building application database')
            build_database(app_database_file, wsjtx_adif_file)
    
    # Read the database into memory.
    with open(app_database_file, 'r') as dbf:
        db = dbf.readlines()
    
    # Initialize the WSJT-X monitor.
    monitor = wsjtxmon(verbose)
    (status, errmsg) = monitor.bind(udp_ip, udp_port, timeout)
    if not status:
        print('Error initializing WSJT-X monitor: {}'.format(errmsg))
        sys.exit(1)
    
    # Initialize current year and julian day.
    utc_now = datetime.now(timezone.utc)
    year_now = utc_now.year
    leap_now = leap_year(year_now)
    julian_now = int(utc_now.strftime('%j'))
    
    # Loop forever until timeout, socket error or WSJT-X application close.
    # Can also use CTRL-C to interrupt and exit.
    ok = True
    while ok:
        try:
            ok = monitor.get_message()
            #print(monitor.Message)
            
            if (monitor.Message[0] == monitor.MSG_CLOSE):
                print('WSJT-X application closed.')
                ok = False
            elif (monitor.Message[0] == monitor.MSG_TIMEOUT):
                print('Socket timeout.')
                ok = False
            elif (monitor.Message[0] == monitor.MSG_SOCKET_ERROR):
                print('Socket error.')
                ok = False
                    
            elif (monitor.Message[0] == monitor.MSG_DECODE):
                # Decoded a message. Parse it and potentially highlight it.
                (call, level) = parse_decode(monitor.Message, db)
                if (level == 1):
                    monitor.send_highlight(
                        call,
                        bg_name=QColor.COLOR_ORANGE,
                        fg_name=QColor.COLOR_WHITE)
                elif (level == 2):
                    monitor.send_highlight(
                        call,
                        bg_name=QColor.COLOR_RED,
                        fg_name=QColor.COLOR_WHITE)
                    
            elif (monitor.Message[0] == monitor.MSG_STATUS):
                # Periodic status message.
                # Get band and mode.
                parse_status(monitor.Message)
                
            elif (monitor.Message[0] == monitor.MSG_HEARTBEAT):
                # Update current date to allow for date rollover.
                utc_now = datetime.now(timezone.utc)
                year_now = utc_now.year
                leap_now = leap_year(year_now)
                julian_now = int(utc_now.strftime('%j'))
                
            elif (monitor.Message[0] == monitor.MSG_QSO_LOGGED):
                # Update database with logged QSO.
                #print(monitor.Message)
                call = monitor.Message[4]
                qso_date = monitor.Message[2]
                (year, leap, julian) = parse_date(qso_date)
                # TODO: Add entry in its correct place instead of sorting the whole database.
                db_entry = '{},{},{},{},{},{}\n'.format(call, wsjtx_mode, wsjtx_band, year, leap, julian)
                db.append(db_entry)
                db.sort()
                with open(app_database_file, 'w') as dbf:
                    dbf.writelines(db)
                logged_count += 1
                print('Logged count: {}'.format(logged_count))
                
        except KeyboardInterrupt:
            ok = False


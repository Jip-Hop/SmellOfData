# What about a VPN which connects via port 80?
# Actually parsing every packet and determining wether or not it's encrypted is very expensive!
# Can't expect a small portable router to do this well
# More naive methods are suitable for this project
# Add email ports?

# Use GPIO 3 for color led, paired state 

from subprocess import Popen, PIPE, check_output
import sys
import re
import datetime
from threading import Timer

limit_channels_on_start = True # good for a demo in static location

mac_regx = re.compile('[\:\-]'.join(['([0-9A-F]{1,2})']*6), re.IGNORECASE)
smell_duration = 1 # in seconds
mac = None
interface = "wlan0"
airodump = None
tcpdump = None

def disable_smell():
    print "disable smell"
    output = Popen(["./smell_state.sh", "off"], stdout=PIPE).communicate()[0]
    print output

def enable_smell():
    print 'enable smell ' + str(datetime.datetime.now())
    output = Popen(["./smell_state.sh", "on"], stdout=PIPE).communicate()[0]
    print output

def return_mac(string):
    found_mac = mac_regx.search(string)
    if(found_mac):
        found_mac = found_mac.group()
        return found_mac

def start_main():
    disable_smell()
    global mac
    try:    
        with open('mac', 'r') as text_file:
            mac=return_mac(text_file.read())

    except:
        print "Error:", sys.exc_info()[0]

    # start a hotspot and wait until a device connects
    if not mac:
        print "Start hotspot"
        check_output("uci set wireless.@wifi-iface[0].mode='ap'; uci set wireless.@wifi-iface[0].ssid='SoD "+str(datetime.datetime.now()).split('.')[0]+"'; uci set wireless.@wifi-iface[0].encryption='none'; uci set wireless.@wifi-iface[0].hidden=0; uci set wireless.@wifi-device[0].disabled=0; uci commit wireless; wifi", shell=True)

        # indicate via LED the MAC isn't locked
        output = Popen(["./mac_locked.sh", "off"], stdout=PIPE).communicate()[0]
        print output

        while not mac:
            output = Popen(["iwinfo", interface, "assoclist"], stdout=PIPE).communicate()[0]
            mac = mac_regx.search(output)
            if(mac):
                mac = mac.group()
                with open("mac", "w") as text_file:
                    text_file.write(mac)

    print mac
    start_monitoring()

def start_monitoring():
    # Indicate via LED the mac is locked
    output = Popen(["./mac_locked.sh", "on"], stdout=PIPE).communicate()[0]
    print output
    timer = None
    tried = False
    applied = False
    channels = []

    # Detect channels with open WiFi networks so airodump-ng can hop only those
    if limit_channels_on_start:
        while not applied:
            output = Popen(["iwinfo"], stdout=PIPE).communicate()[0]
            # Wait until ap mode mode is applied
            if(output.find("Mode: Master") > -1 and output.find("Channel: unknown") == -1):
                applied = True
            elif tried == False:
                check_output("uci set wireless.@wifi-iface[0].mode='ap'; uci set wireless.@wifi-iface[0].hidden=1; uci commit wireless; wifi", shell=True)
                tried = True
        # Reset variables, will be reused
        tried = False
        applied = False

        output = Popen(["iwinfo", interface, "scan"], stdout=PIPE).communicate()[0]
        output = output.splitlines()
        
        channel_regex = re.compile(ur'Channel: (\d*)')
        channel = None
        
        # Retrieve all the channels with open WiFi networks
        for line in output:
            result = re.search(channel_regex, line)
            if result:
                channel = result.group(1)
            elif line.find("          Encryption: none") > -1:
                channels.append(channel)

    # Wait until monitor mode has been applied
    while not applied:
        output = Popen(["iwinfo"], stdout=PIPE).communicate()[0]
        #print output
        # Wait until monitor mode is applied and we're actually monitoring on a specific channel
        if(output.find("Mode: Monitor") > -1 and output.find("Channel: unknown") == -1):
            applied = True
        elif tried == False:
            check_output("uci set wireless.@wifi-iface[0].mode='monitor'; uci commit wireless; wifi", shell=True)
            tried = True

    if len(channels) == 1:
        # No need to start airodump to channel-hop, just 1 channel - set to this channel:
        check_output('iw dev ' + interface + ' set channel ' + str(channels[0]), shell=True)
    else:
        airodump_command = ['airodump-ng',interface, '-a', '--encrypt', 'opn']
        if len(channels) > 1:
            # Hop only the channels with open WiFi networks -- initialized once, doesn't update dynamically: good enough for demo in static location
            airodump_command.append('--channel')
            airodump_command.append(",".join(channels))
        # if len(channels) == 0 then keep hopping all channels
        # Fire up airodump because it is very efficient with channel hopping
        airodump = Popen(airodump_command, stdout=PIPE,stderr=PIPE)

    # Make TCPdump packet-buffered with -U,
    # now the callback function will fire on each filtered packet
    # only port 80 and 53 are monitored, regardless of which data is actually going over these ports (encrypted or not)
    # ftp traffic is not monitored, not used as often as http by novice users,
    # and is likely more dependant on server config (non default ports)

    tcpdump = Popen(('tcpdump', '-U', '-i', interface, 'ether host ' + mac + ' and tcp port 80 or udp port 53'), stdout=PIPE)
    for line in tcpdump.stdout:
        #print row.rstrip()   # process packet here
        enable_smell()
        # Keep on smelling, cancel current timer and schedule new one in the future
        if timer:
            timer.cancel()
        timer = Timer(smell_duration, disable_smell)
        timer.start()

start_main()
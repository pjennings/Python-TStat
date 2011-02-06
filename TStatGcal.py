#!/usr/bin/env python

#Copyright (c) 2011, Paul Jennings <pjennings-tstat@pjennings.net>
#All rights reserved.

#Redistribution and use in source and binary forms, with or without 
#modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice, 
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * The names of its contributors may not be used to endorse or promote
#      products derived from this software without specific prior written
#      permission.

#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
#IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
#SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
#INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
#CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
#ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF 
#THE POSSIBILITY OF SUCH DAMAGE.

VERSION = 1.0

# TStatGcal.py
# Script to pull commands from Google Calendar and update thermostat.
#
# Requirements:
# * gdata (http://code.google.com/p/gdata-python-client/)
# * ElementTree (http://effbot.org/zone/element-index.htm)
# * Python-TStat (same place you got this script)
#
# Usage:
# 1. Create a Google/GMail account (or Google Apps for domains).
# 2. Go to http://calendar.google.com
# 3. Create a calendar (called "Thermostat" for example).
# 4. Add events with titles of the form:
#    "Heat 70"  -- sets heat to 70 degrees
#    "Cool 70"  -- sets cool to 70 degrees
#    "Fan On"   -- forces fan on
#    "Mode Off" -- forces system off
# 5. Run the following commands (assuming Unix/Linux system):
#    echo "youraccount@gmail.com" >> ~/.google
#    echo "yourpassword" >> ~/.google
#    chmod 400 ~/.google
#    (where "youraccount@gmail.com" is the account that you created in 
#     step 1 and "yourpassword" is your password)
# 6. Add the following to your crontab to run every 5 minutes or so:
#      TStatGcal.py <thermostat_address> <calendar_name>
#    Where <thermostat_address> is the IP address of your thermostat 
#    and <calendar_name> is the name of the calendar you created in 
#    step 3.
#
# Notes:
#    In order to limit the chance that this script sets your 
#    thermostat to dangerous settings (e.g. too low or off during 
#    the winter, there are some override variables below:
#      HEAT_MIN, HEAT_MAX: Minimum/maximum setting for heat
#      COOL_MIN, COOL_MAX: Minimum/maximum setting for cool
#      COMMANDS: What parts of the thermostat the script is 
#                allowed to control
#
#    Set the HEAT/COOL variables to appropriate values for your 
#    situation.  By default, this script will not set the 
#    thermostat mode (on/off/auto).  You probably want to leave 
#    it on auto.  This is to prevent a hacker (or a typo) from 
#    turning your furnace off during the winter.  
#
#    By default, this script does not disable cloud updates. 
#    That way, if this script does not run for some reason (e.g. 
#    if your computer crashes), you can still have a reasonable 
#    backup program running.  When the cloud updates your thermostat,
#    there may be a short period where the setting does not match
#    what is on your calendar.  If this behavior is undesirable, you
#    can disable cloud updates.  
#
#    At the start time of your event, the script will set the 
#    the thermostat to the requested setting.  The duration of the 
#    events on your calendar is ignored.  For example, a simple
#    program might look like this:
#      6:30 -- Heat 70
#      8:00 -- Heat 60
#     16:00 -- Heat 70
#     22:00 -- Heat 60
#    In order to create this program in your calendar, you would need 
#    four events.  If you create a "Heat 70" event that lasts from 
#    6:30-22:00 and an overlapping "Heat 60" event that lasts from 
#    8:00-16:00, you will effectively miss the "Heat 70" command at 
#    16:00.  Only the start time of the event is used.  

# Minimum and maximum values for heat and cool
# The script will never set values outside of this range
HEAT_MIN = 55
HEAT_MAX = 80
COOL_MIN = 70
COOL_MAX = 100

# Valid commands
# Remove commands that you don't want the script to execute here
# mode in particular can be dangerous, because someone could create 
# a 'mode off' command and turn your heat off in the winter.
#COMMANDS = ['Heat', 'Cool', 'Mode', 'Fan']
COMMANDS = ['Heat', 'Cool', 'Fan']

try:
  from xml.etree import ElementTree # for Python 2.5 users
except ImportError:
  from elementtree import ElementTree
import gdata.calendar.service
import gdata.service
import atom.service
import gdata.calendar

import atom
import datetime
import getopt
import os
import sys
import string
import time

import TStat

def main(tstatAddr, commandMap=None, username=None, password=None, calName="Thermostat"):
	# Connect to thermostat
	tstat = TStat.TStat(tstatAddr)

	# Command map is used to translate things like "Wake" into "Heat 70"
	if commandMap is None:
		commandMap = {}

	# Log in to Google
	calendar_service = gdata.calendar.service.CalendarService()
	calendar_service.email = username
	calendar_service.password = password
	calendar_service.source = "TStatGCal-%s" % VERSION
	calendar_service.ProgrammaticLogin()

	# Create date range for event search
	today = datetime.datetime.today()
	gmt = time.gmtime()
	gmtDiff = datetime.datetime(gmt[0], gmt[1], gmt[2], gmt[3], gmt[4]) - today
	tomorrow = datetime.datetime.today()+datetime.timedelta(days=2)

	query = gdata.calendar.service.CalendarEventQuery()
	query.start_min = "%04i-%02i-%02i" % (today.year, today.month, today.day)
	query.start_max = "%04i-%02i-%02i" % (tomorrow.year, tomorrow.month, tomorrow.day)

	# Look for a calendar called calName
	feed = calendar_service.GetOwnCalendarsFeed()
	for i, a_calendar in enumerate(feed.entry):
		if a_calendar.title.text == calName:
			query.feed = a_calendar.content.src

	if query.feed is None:
		print "No calendar with name '%s' found" % calName
		return

	# Search for the event that has passed but is closest to the current time
	# There is probably a better way to do this...
	closest = None
	closestDT = None
	closestWhen = None
	closestEvent = None
	closestCommand = None
	closestValue = None
	feed = calendar_service.CalendarQuery(query)
	for i, an_event in enumerate(feed.entry):
		#print '\t%s. %s' % (i, an_event.title.text,)

		# Try to map named time period into actual command
		text = an_event.title.text.strip()
		if commandMap.has_key(text):
			text = commandMap[text]

		print "Translated %s into %s" % (an_event.title.text.strip(), text)

		# Skip events that are not valid commands
		try:
			(command, value) = text.splitlines()[0].split()
		except:
			command = text
		if command not in COMMANDS:
			print "Warning: '%s' is not a valid command" % text
			continue
		try:
			float(value)
		except:
			if value not in ['Off', 'On', 'Auto']:
				print "Warning: '%s' is not a valid command" % an_event.title.text
				continue
		for a_when in an_event.when:
			d = a_when.start_time.split("T")[0]
			t = a_when.start_time.split("T")[1].split(".")[0]
			(year, month, day) = [int(p) for p in d.split("-")]
			(hour, min, sec) = [int(p) for p in t.split(":")]
			dt = datetime.datetime(year, month, day, hour, min, sec)-gmtDiff
			#print "DT:", dt
			d = dt-datetime.datetime.today()
			#print "d.days:", d.days

			# Skip events that are in the future
			if d.days >= 0:
				continue

			if closest is None:
				closest = d
				closestDT = dt
				closestWhen = a_when
				closestEvent = an_event
				closestCommand = command
				closestValue = value
			else:
				if d.days < closest.days:
					continue
				if d.seconds > closest.seconds:
					closest = d
					closestDT = dt
					closestWhen = a_when
					closestEvent = an_event
					closestCommand = command
					closestValue = value

	if closestEvent is None:
		print "No events found"
		return

	text = closestEvent.title.text
	print "Closest event: %s at %s" % (text, closestDT)
	#(command, value) = text.splitlines()[0].split()
	command, value = (closestCommand, closestValue)
	if command == 'Heat':
		value = int(value)
		if value >= HEAT_MIN and value <= HEAT_MAX:
			print "Setting heat to %s" % int(value)
			tstat.setHeatPoint(value)
		else:
			print "Value out of acceptable heat range:", value
	elif command == 'Cool':
		value = int(value)
		if value >= COOL_MIN and value <= COOL_MAX:
			print "Setting cool to %s" % value
			tstat.setCoolPoint(int(value))
		else:
			print "Value out of acceptable cool range:", value
	elif command == 'Fan':
		print "Setting fan to %s" % value
		tstat.setFanMode(value)
	elif command == 'Mode':
		print "Setting mode to %s" % value
		tstat.setTstatMode(value)

if __name__ == '__main__':
	f = open(os.path.expanduser("~/.google"))
	username = f.readline().splitlines()[0]
	password = f.readline().splitlines()[0]
	f.close()
	if os.path.isfile(os.path.expanduser("~/.tstat_commands")):
		commandMap = {}
		f = open(os.path.expanduser("~/.tstat_commands"))
		for line in f.readlines():
			key, value = line.split(":")
			commandMap[key] = value
		f.close()
	main(sys.argv[1], username=username, password=password, calName=sys.argv[2], commandMap=commandMap)

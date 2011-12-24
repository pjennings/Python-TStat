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

# API.py
# API definitions for Radio Thermostat wifi-enabled thermostats.

# This file allows multiple APIs to be defined for different versions of the 
# thermostat hardware/software.  Currently there is only one API defined, for 
# the 3M-50/CT30.  Each API should be defined as a subclass of API.  You must 
# define models and versions to be a list of versions and models (as retrieved
# from the thermostat) that your API subclass supports.  entries must be 
# defined as a dict such that the keys are named pieces of data and the values 
# are instances of APIEntry.  (See APIv1 for an example.)
#
# Example APIEntry:
#		'fmode': APIEntry(
#			[('/tstat/fmode', 'fmode'), ('/tstat', 'fmode')],
#			[('/tstat/fmode', 'fmode')],
#			{'0': 'Auto', '1': '??', '2':'On'} #TODO: Check these values
#		)
# APIEntry has three members:
# 	getters:  A list of tuples where the first entry is a URL on the thermostat
#             and the second entry is the JSON key used to retrieve the piece 
#             of data.  In the above example, fmode can be retrieved either 
#             from /tstat/fmode using key fmode, or from /tstat using key 
#             fmode.  Multiple values are allowed here to help support 
#             changes in hardware API.  If fmode is removed from the /tstat 
#             output, the system will automatically fall back to /tstat/fmode.
#   setters:  A list of tuples in the same format as getters, used for setting
#             values.
#   valueMap: A dict of possible outputs and the human-readable value they 
#             should be mapped to.  In the above example, fmode=0 is mapped to
#             'Auto', while fmode=2 is mapped to 'On'.  
#
# Extending an existing API:
#   Assume that in a new hardware/software revision, power usage data in KWH is
#   available at /tstat/kwh.  A new API could be defined as follows:
#
# class APIv2(APIv1):
#     def __init__(self):
#         self.entries['fmode'].getters = [('/tstat/kwh', 'kwh')]
#
#   You would most likely also want to add access functions to TStat.py as 
#   well.

class APIEntry:
	def __init__(self, getters, setters, valueMap=None, usesJson=True):
		self.getters = getters
		self.setters = setters
		self.valueMap = valueMap
		self.usesJson = usesJson

class API:
	models = []
	successStrings = []
	entries = None

	def __getitem__(self, item):
		return self.entries[item]

	def has_key(self, key):
		return self.entries.has_key(key)

	entries = {
		'model': APIEntry(
			[('/tstat/model', 'model')],
			[]
		)
	}

class API_CT50v109(API):
	models = ['CT50 V1.09']
	successStrings = [
						"Tstat Command Processed",
						"Cloud updates have been suspended till reboot",
						"Cloud updates activated"
	]
	entries = {
		'fmode': APIEntry(
			[('/tstat/fmode', 'fmode'), ('/tstat', 'fmode')],
			[('/tstat/fmode', 'fmode')],
			{0: 'Auto', 1: '??', 2:'On'} #TODO: Check these values
		),
		'tmode': APIEntry(
			[('/tstat/tmode', 'tmode'), ('/tstat', 'tmode')],
			[('/tstat/tmode', 'tmode')],
			{0: 'Off', 1: 'On'} #TODO: Check these values
		),
		'temp': APIEntry(
			[('/tstat', 'temp'), ('/temp', 'temp')],
			[]
		),
		'override': APIEntry(
			[('/tstat', 'override'), ('/tstat/info', 'override'), ('/tstat/override', 'override')],
			[],
			{0: False, 1: True}
		),
		'hold': APIEntry(
			[('/tstat', 'hold'), ('/tstat/info', 'hold'), ('/tstat/hold', 'hold')],
			[('/tstat/hold', 'hold')],
			{0: False, 1: True}
		),
		't_heat': APIEntry(
			[('/tstat/info', 't_heat'), ('/tstat/ttemp', 't_heat')],
			[('/tstat/ttemp', 't_heat')]
		),
		't_cool': APIEntry(
			[('/tstat/info', 't_cool'), ('/tstat/ttemp', 't_cool')],
			[('/tstat/ttemp', 't_cool')]
		),
		'tstate': APIEntry(
			[('/tstat', 'tstate')],
			[],
			{0: 'Off', 1: 'On'}
		),
		'fstate': APIEntry(
			[('/tstat', 'fstate')],
			[],
			{0: 'Off', 1: 'On'}
		),
		'day': APIEntry(
			[('/tstat', 'time/day')],
			[],
			{0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}
		),
		'hour': APIEntry(
			[('/tstat', 'time/hour')],
			[]
		),
		'minute': APIEntry(
			#[('/tstat', 'time/minute'), ('/tstat/time/minute', 'day')],
			[('/tstat', 'time/minute')],
			[]
		),
		'today_heat_runtime': APIEntry(
			[('/tstat/datalog', 'today/heat_runtime')],
			[]
		),
		'today_cool_runtime': APIEntry(
			[('/tstat/datalog', 'today/cool_runtime')],
			[]
		),
		'yesterday_heat_runtime': APIEntry(
			[('/tstat/datalog', 'yesterday/heat_runtime')],
			[]
		),
		'yesterday_cool_runtime': APIEntry(
			[('/tstat/datalog', 'yesterday/cool_runtime')],
			[]
		),
		'errstatus': APIEntry(
			[('/tstat/errstatus', 'errstatus')],
			[],
			{0: 'OK'}
		),
		'model': APIEntry(
			[('/tstat/model', 'model')],
			[]
		),
		'power': APIEntry(
			[('/tstat/power', 'power')],
			[('/tstat/power', 'power')]
		),
		'cloud_mode': APIEntry(
			[],
			[('/cloud/mode', 'command')],
			usesJson=False
		)
		#'eventlog': #TODO
	}

class API_CT30v192(API_CT50v109):
		models = ['CT30 V1.92']

APIs = [API_CT50v109, API_CT30v192]

def getAPI(model):
	for api in APIs:
		if model in api.models:
			return api()

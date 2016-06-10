#!/usr/bin/env python

import argparse
import urllib2
import base64
import keyring
import getpass
import ConfigParser
import webbrowser
import os
import sys
from jira.client import JIRA
from jira.exceptions import JIRAError

parser = argparse.ArgumentParser(description='MongoDB Jira attachments download tool')
parser.add_argument('ticket', action='store', nargs='?', help='ticket number, e.g. CS-1234')
parser.add_argument('--username', action='store', help='provide your username for this and future calls to mflux.')
parser.add_argument('--path', action='store', help='provide your ticket path for this and future calls to mflux.')
parser.add_argument('--reset-password', action='store_true', help='use this flag to reset your password. You will be prompted for a new one.')
parser.add_argument('--web', '-w', action='store_true', help='opens a webbrowser for that ticket.')
args = vars(parser.parse_args())

# initialize variables
username = None
password = None
ticket_path = None

# load config file if available
home = os.path.expanduser("~")
cfg_dir = os.path.join(home, '.mflux')
cfg_file = os.path.join(cfg_dir, 'config')
config = ConfigParser.ConfigParser()

if os.path.exists(cfg_file):
	# load username and ticket_path from config file
	config.read(cfg_file)
	username = config.get('DEFAULT', 'username')
	ticket_path = config.get('DEFAULT', 'ticket_path')

if args['username']:
	username = args['username']
	config.set('DEFAULT', 'username', username)

if not username:
	username = raw_input("enter your Jira username: ")
	config.set('DEFAULT', 'username', username)

password = keyring.get_password('mflux', username)
if password and args['reset_password']:
	password = None
	keyring.delete_password('mflux', username)

if not password:
	password = getpass.getpass("enter your Jira password (it will be stored securely in the keychain): ")
	keyring.set_password('mflux', username, password)

if args['path']:
	ticket_path = args['path']
	config.set('DEFAULT', 'ticket_path', ticket_path)

if not ticket_path:
	ticket_path = os.path.expanduser(raw_input("enter the path where you want to store your tickets: "))
	config.set('DEFAULT', 'ticket_path', ticket_path)

# store username and ticket_path in config file
if not os.path.exists(cfg_dir):
	os.makedirs(cfg_dir)
config.write(open(cfg_file, 'w'))

# create jira object
auth = (username, password)
opt = {'server': 'https://jira.mongodb.org', "verify": False}
jira = JIRA(options = opt, basic_auth = auth)

# get jira issue, either specified or by current folder name
ticket_no = args['ticket'] or os.path.split(os.getcwd())[1]

# load webpage if requested (early to distract user)
if args['web']:
	print "opening ticket in browser"
	webbrowser.open_new_tab('https://jira.mongodb.org/browse/%s' % ticket_no)

# access jira
try:
	issue = jira.issue(ticket_no)
except JIRAError as e:
	if e.status_code == 404:
		raise SystemExit("Jira issue %s not found" % ticket_no)
	elif e.status_code == 401:
		keyring.delete_password('mflux', username)		
		raise SystemExit("Authorization failed as user %s, please check password" % username)
	else:
		raise SystemExit("Unknown error occured: %s" % e.text)


# check if directory exists, if not create it
directory = os.path.join(ticket_path, ticket_no)

if not os.path.exists(directory):
	print "creating %s" % directory
	os.makedirs(directory)

# change into ticket directory
os.chdir(directory)

# download attachments
attach_count = len(issue.fields.attachment)
if attach_count > 0:
	for att in issue.fields.attachment:
		# check if file is already downloaded
		if os.path.exists(os.path.join(directory, att.filename)):
			continue
		
		print "downloading %s" % att.filename

		# build request with basic auth header
		base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
		req = urllib2.Request(att.content)
		req.add_header("Authorization", "Basic %s" % base64string)

		# access file and store
		response = urllib2.urlopen(req)
		att_file = response.read()
		with open(att.filename, 'wb') as f:
			f.write(att_file)


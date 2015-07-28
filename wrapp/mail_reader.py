#!/usr/bin/env python

import sys
import imaplib
import getpass
import email
import datetime
import re
import pymongo
import time
import push_notify
import socket

#Global settings
USERNAME = '<EMAIL>'
PASSWORD = '<PASSWORD>'

#AP filters
ap_email = "Mongo@beanmix.com"
ap_subject_srch = re.compile(r'Alphapage message')
ap_caller_srch = re.compile(r'\|Caller: (.*) \`\|')
ap_company_srch = re.compile(r'\|Company: (.*) \`\|')
ap_location_srch = re.compile(r'\|Location: (.*) \`\|')
ap_phone_srch = re.compile(r'\|Phone: (.*) \`\|')
ap_jira_srch = re.compile(r'\|JIRA #: (.*) \`\|')
ap_priority_srch = re.compile(r'\|Priority: (.*) \`\|')
ap_message_srch = re.compile(r'\|Message: (.*)\|')

#Info@10gen.com filters
info_email = "info@10gen.com"
info_reporter_srch = re.compile(r'Reporter: (.*) from (.*) \((.*)\)')

def process_ap(text):
  try:
     caller = ap_caller_srch.search(text).group(1)
  except:
     caller = None

  try:
     company = ap_company_srch.search(text).group(1)
  except:
     company = None

  try:
     location = ap_location_srch.search(text).group(1)
  except:
     location = None

  try:
     phone = ap_phone_srch.search(text).group(1)
  except:
     phone = None

  try:
     jira = ap_jira_srch.search(text).group(1)
  except:
     jira = None

  try:
     prio = ap_priority_srch.search(text).group(1)
  except:
     prio = None

  try:
     message = ap_message_srch.search(text).group(1)
  except:
     message = None

  print "Recieved AP from", caller, company, location, phone, jira, prio, message
  res = push_notify.notify("AP: " + caller + " from " + company, text)
  print res

def process_info(text):
  try:
     reporter, group = info_reporter_srch.search(text).group(1,2)
  except:
     reporter = None
     group = None

  print "Recieved misfiled ticket note from", reporter, group
  res = push_notify.notify("Misfiled ticket: " + reporter + " from " + group, text)
  print res

def process_email(sender,subject,date,text):
  from_email = email.utils.parseaddr(sender)[1]
  if (from_email.lower() == ap_email.lower()) and ap_subject_srch.search(subject):
      process_ap(text)
  elif (from_email.lower() == info_email.lower()):
      process_info(text)
  else:
      print "\nDon't know what do to with this one..."
      print "From:", sender
      print 'Message subject:', subject
      print 'Raw Date:', date
      print "\n"

def process_mailbox(M):
  #rv, data = M.search(None, "UNSEEN")
  rv, data = M.search(None, '(UNSEEN OR (HEADER FROM "Mongo@beanmix.com") (HEADER FROM "info@10gen.com"))') #temporary fliter to avoid parsing all my personal messages
  if rv != 'OK':
      print "No messages found!"
      return

  for num in data[0].split():
      rv, data = M.fetch(num, '(RFC822)')
      if rv != 'OK':
          print "ERROR getting message", num
          return
      msg = email.message_from_string(data[0][1])
      data = msg.get_payload()
      if data:
          if msg.is_multipart(): # I think data[0] is a text version
             process_email(msg['From'],msg['Subject'],msg['Date'],data[0])
          else:
             process_email(msg['From'],msg['Subject'],msg['Date'],data)

M = None

try: # We stop on ^C
   while True:
      try: # We need to recover from all kinds of errors
          M = imaplib.IMAP4_SSL('imap.gmail.com')

          try:
              M.login(USERNAME, PASSWORD)
          except imaplib.IMAP4.error:
              print "LOGIN FAILED!!! "
              sys.exit()

          while True:
              rv, data = M.select("inbox")
              if rv == 'OK':
                  print "Processing mailbox...\n"
                  process_mailbox(M)
                  time.sleep(30)
              else:
                  print "ERROR: Unable to open mailbox ", rv
                  time.sleep(15)
      except socket.error, e:
          print "Socket exception", e
          print "Attempting a reconnect after 30 seconds\n"
          time.sleep(30)
      except imaplib.IMAP4.error, e:
          print "imaplib exception", e
          print "Attempting a reconnect after 30 seconds\n"
          time.sleep(30)
except KeyboardInterrupt:
   pass

if M != None:
  M.close()
  M.logout()

print "Exiting now"


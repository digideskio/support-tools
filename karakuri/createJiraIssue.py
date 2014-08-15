import os
import pymongo
import random
import sys
import time

from ConfigParser import RawConfigParser
from jirapp import jirapp
from optparse import OptionParser
from supportissue import SupportIssue

#
# Process command line parameters with a system of tubes
#
parser = OptionParser()
parser.add_option("-c", "--config", default="karakuri.cfg",
                  help="configuration file FILE", metavar="FILE")
parser.add_option("-d", "--description",
                  help="description file FILE", metavar="FILE")
parser.add_option("-g", "--group",
                  help="JIRA group/company GROUP", metavar="GROUP")
parser.add_option("-i", "--priority",
                  help="ticket priority PRIORITY, e.g. 1, 2, 3, etc.")
parser.add_option("-l", "--labels",
                  help="ticket label(s), comma separated")
parser.add_option("--live", action="store_true",
                  help="create the ticket irl")
parser.add_option("-o", "--owner",
                  help="issue owner OWNER")
parser.add_option("-p", "--project",
                  help="issue project PROJECT")
parser.add_option("-r", "--reporter",
                  help="issue reporter REPORTER")
parser.add_option("-s", "--summary",
                  help="issue summary SUMMARY")
parser.add_option("-t", "--type", dest="issuetype",
                  help="issue type TYPE, e.g. Bug, Proactive, etc.")
(options, args) = parser.parse_args()

# Configuration error found, aborting
error = False

if not options.config:
    print("Error: specify a configuration file")
    error = True
else:
    # TODO expand to full path and verify readability of configuration file
    pass
if not options.description:
    print("Error: specify a description file")
    error = True
else:
    # TODO expand to full path and verify readability of description file
    pass
if not options.group:
    # TODO make this optional?
    print("Error: specify a JIRA group/company for the ticket")
    error = True
else:
    # TODO validate with jira lookup
    pass
if options.priority:
    # TODO validate integer in range
    pass
else:
    options.priority = 3
if options.live is None:
    options.live = False
if options.project:
    # TODO validate with jira lookup
    pass
else:
    options.project = "CS"
if not options.summary:
    print("Error: specify a summary for the ticket")
    error = True
else:
    # TODO validate string?
    pass
if options.issuetype:
    # TODO validate with jira lookup
    pass
else:
    options.issuetype = "Problem Ticket"

if options.issuetype == "Proactive":
    options.reporter = "proactive-support"
if options.reporter:
    # TODO validate
    pass
if error:
    sys.exit(1)

#
# Parse configuration file and initialize JIRA++
#
config = RawConfigParser()
config.read(os.getcwd() + "/" + options.config)

descriptionfile = open(options.description, 'r')
description = descriptionfile.read()

conn = pymongo.MongoClient()
db = conn.jirameta

jira = jirapp(config, db)
jira.setLive(options.live)

# Set random seed
random.seed(time.localtime())

issue_config = {'description': description,
                'group': options.group,
                'issuetype': options.issuetype,
                'owner': options.owner,
                'priority': options.priority,
                'project': options.project,
                'reporter': options.reporter,
                'summary': options.summary
                }

# Labels are optional
if options.labels:
    issue_config['labels'] = options.labels

# Until the meta validation is available, add for DAN
if options.project == "DAN":
    issue_config['company groups'] = {'name': options.group}

issue = jira.createIssue(SupportIssue(issue_config).getJIRAFields())

# Update with labels if specified
if 'labels' in options:
    jira.setLabels(issue, options['labels'])

# Set owner if specified
if 'owner' in options and options['owner'] != "":
    jira.setOwner(issue, options['owner'])

# Set Proactive tickets to Waiting for Customer
if issue_config['issuetype'].lower() == "proactive":
    jira.wfcIssue(issue)

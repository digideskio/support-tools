import os
import random
import sys
import time

from ConfigParser import RawConfigParser
from JIRApp import JIRApp
from optparse import OptionParser
from ProactiveSupport import get, jira_users, renderDescription

#
# Process command line parameters with a system of tubes
#
parser = OptionParser()
parser.add_option("-c", "--config", default="jira.cfg",
                  help="configuration file FILE", metavar="FILE")
parser.add_option("-d", "--description",
                  help="templated description file FILE", metavar="FILE")
parser.add_option("-g", "--group",
                  help="JIRA group GROUP", metavar="GROUP")
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

error = False

if not options.config:
    print("Error: specify a configuration file")
    error = True
else:
    # TODO expand to full path and verify readability of configuration file
    pass
if not options.description:
    print("Error: specify a description template")
    error = True
else:
    # TODO expand to full path and verify readability of description template
    pass
if not options.group:
    print("Error: specify a group for the ticket")
    error = True
else:
    # TODO validate
    pass
if options.priority:
    # TODO validate
    pass
else:
    options.priority = 3
if options.live is None:
    options.live = False
if options.project:
    # TODO validate
    pass
else:
    options.project = "CS"
if not options.summary:
    print("Error: specify a summary for the ticket")
    error = True
else:
    # TODO validate
    pass
if options.issuetype:
    # TODO validate
    pass
else:
    options.issuetype = "Proactive"
if options.issuetype.lower() == "proactive":
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
jira = JIRApp(config)
jira.setLive(options.live)

# Set random seed
random.seed(time.localtime())

# Randomize owner
if options.owner:
    user = options.owner
else:
    user = jira_users[random.randint(0, len(jira_users)-1)]
    options.owner = user
template_config = {'NAME': get(user, 'name'),
                   'SIGNOFF': get(user, 'signoff')}

descriptionfile = open(options.description, 'r')
description = descriptionfile.read()
description = renderDescription(description, template_config)

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

jira.createIssue(issue_config)

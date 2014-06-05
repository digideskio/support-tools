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
parser.add_option("--live", action="store_true",
                  help="create the ticket irl")
parser.add_option("-s", "--summary",
                  help="issue summary SUMMARY")
(options, args) = parser.parse_args()

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
    print("Error: specify a group for the ticket")
    error = True
else:
    # TODO expand to full path and verify readability of description file
    pass
if options.live is None:
    options.live = False
if not options.summary:
    print("Error: specify a summary for the ticket")
    error = True
else:
    # TODO perform basic validation
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

# Randomize reporter
user = jira_users[random.randint(0, len(jira_users)-1)]
template_config = {'NAME': get(user, 'name'),
                   'SIGNOFF': get(user, 'signoff')}

descriptionfile = open(options.description, 'r')
description = descriptionfile.read()
description = renderDescription(description, template_config)

issue_config = {'summary': options.summary,
                'description': description,
                'group': options.group
                }

jira.createProactiveIssue(issue_config)

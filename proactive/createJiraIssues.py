import os

from jira.client import JIRA
from pprint import pprint
from ConfigParser import RawConfigParser

# To do or not to do, that is this Boolean
live = False

config = RawConfigParser()
config.read(os.getcwd() + '/jira.cfg')

opts = {'server': 'https://jira.mongodb.org', "verify": False}
auth = (config.get('JIRA', 'username'), config.get('JIRA', 'password'))
jira = JIRA(options=opts, basic_auth=auth)

groups = ["adorsys",
          "Adorsys - TRUSTCODE",
          "ADP",
          "amobee",
          "Apple - Social Store",
          "B2B_BW",
          "barnesandnoble",
          "BMC - Cert BMC Tools",
          "CECity",
          "Cisco - EIFDBA Team",
          "Citigroup - Dev Support",
          "DoD - GWS",
          "Dreamworks Animation",
          "Dynafleet-CPN",
          "Expedia Search Solutions",
          "Expedia_GIS",
          "Gamesys",
          "HPGDS",
          "John Deere",
          "Lola Enterprises - Customer Transformation",
          "MediaOcean",
          "Nike - PtP",
          "Northgate Arinso",
          "Panera - Online Ordering",
          "pclndba",
          "Server Density Ltd",
          "Square Enix",
          "Staples",
          "TicketMaster",
          "UHC.com",
          "UPMC",
          "VMware - Praxis Portal",
          "webmd"]

user_dict = {}
user_dict["jacob.ribnik"] = {'name': "Jake",
                             'signoff': "Jake"}
user_dict["ruairi.newman"] = {'name': "Ruairi",
                              'signoff': "Regards,\n\nRuairi"}

users = user_dict.keys()

counter = 0
for group in groups:
    useri = counter % 2
    counter += 1

    summary = 'MongoDB Proactive: OnPrem MMS Backup Critical Bug Advisory'
    description = "Hello,\n\nMy name is " + user_dict[users[useri]]['name'] +\
                  """ and I am a member of the Proactive Technical Support team
                  here at MongoDB, Inc. Proactive Support is a new initiative
                  to identify issues in your MongoDB deployment before they
                  become problematic.

                  We have identified a bug introduced in the 1.4.0 release of
                  OnPrem MMS that impacts users backing up MongoDB 2.6 replica
                  sets and sharded clusters. This issue affects deployments
                  that include user or custom role definitions and can result
                  in the loss of these definitions on restore.

                  MMS 1.4.2 contains the fix for this bug and is available now
                  at:

                  http://www.mongodb.com/subscription/downloads/mms

                  After updating you should perform a new initial sync to
                  ensure the role definitions are included in the backup.

                  This release additionally improves restore times and is a
                  valuable update regardless. For more information about the
                  release see the changelog at:

                  https://mms.mongodb.com/help-hosted/v1.4/release-notes/application/#mms-server-1-4-2

                  Please let us know if you have any questions about the bug,
                  or would like assistance with the update, by commenting in
                  this ticket.
                  """ + user_dict[users[useri]]['signoff']

    issue_dict = {
        'project': {'key': 'CS'},
        'summary': summary,
        'description': description,
        'issuetype': {'name': 'Proactive'},
        'priority': jira.priority('3').raw,
        'reporter': {'name': 'proactive-support'},
        #        'customfield_10041': {'name': users[useri]},
        'customfield_10030': {'name': group}
        }

    print("Creating ticket...")

    if live:
        issue = jira.create_issue(fields=issue_dict)
    else:
        issue = {}
        issue['raw'] = issue_dict

    print("Created ticket:")
    pprint(issue)

    if live:
        # (u'761', u'Wait for Customer')
        res = jira.transition_issue(issue, '761')
        pprint(res)
    else:
        res = True

    if res:
        print("--> transition to WFC")

import sys

from jira.client import JIRA
from jira.exceptions import JIRAError
from JIRAIssue import JIRAIssue


class JIRApp(JIRA):
    """ JIRA++ is JIRA+1. Use it to profit. """
    def __init__(self, config):
        # By default we sit here and look pretty
        # All talk, no walk
        self.live = False

        opts = {'server': 'https://jira.mongodb.org', "verify": False}
        auth = (config.get('JIRA', 'username'), config.get('JIRA', 'password'))

        JIRA.__init__(self, options=opts, basic_auth=auth)

    def createIssue(self, params={}):
        """ This method creates a JIRA issue """
        # TODO validate issue meta is sufficient to
        # successfully create the ticket
        issue = JIRAIssue(self, params)

        print "Creating issue..."

        if self.live:
            try:
                issue = self.create_issue(fields=issue.data)
                print "Created %s" % issue.key
            except JIRAError:
                e = sys.exc_info()[0]
                print "JIRApp.createIssue: ", e
        else:
            issue.dump()

        # Update with labels if specified
        if 'labels' in params:
            self.setLabels(issue, params['labels'])

        # NOTE must call setOwner before setWFC for reasons unknown
        # JIRA allows transitions in this order but not the other
        if 'owner' in params and params['owner'] != "":
            self.setOwner(issue, params['owner'])

        if params['issuetype'].lower() == "proactive":
            self.setWFC(issue)

        return issue

    def setLabels(self, issue, labels):
        """ This method sets the labels in a JIRA issue """
        # TODO validate labels is a string that will return [] on split
        print "Setting labels..."

        if self.live:
            try:
                issue.update(labels=labels.split(','))
                print "Updated %s" % issue.key
            except JIRAError:
                e = sys.exc_info()[0]
                print "JIRApp.setLabels: ", e
        else:
            print "beep boop boop beep boop"

    def setLive(self, b):
        """ Lock and load? """
        self.live = b

    def setOwner(self, issue, owner):
        """ This method sets the JIRA issue owner using the Internal Fields
        transition """
        print "Setting owner..."

        if self.live:
            try:
                # (u'831', u'Internal Fields')
                fields = {'customfield_10041': {'name': owner}}
                self.transition_issue(issue, '831', fields=fields)
                print "Transitioned %s" % issue.key
            except JIRAError:
                e = sys.exc_info()[0]
                print "JIRApp.setOwner: ", e
        else:
            print "beep boop boop beep boop"

    def setWFC(self, issue):
        """ This method sets the status of a ticket to Wait for Customer """
        print "Setting WFC..."

        if self.live:
            try:
                # (u'761', u'Wait for Customer')
                self.transition_issue(issue, '761')
                print "Transitioned %s" % issue.key
            except JIRAError:
                e = sys.exc_info()[0]
                print "JIRApp.setWFC: ", e
        else:
            print "beep boop boop beep boop"

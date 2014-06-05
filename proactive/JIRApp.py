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
        """ This method actually creates a JIRA issue """
        issue = JIRAIssue(self, params)
        # TODO validate issue meta is sufficient to
        # successfully create the ticket

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

        return issue

    def createProactiveIssue(self, params={}):
        """ This method creates a ticket of type Proactive
        and sets it to Wait for Customer """
        issue = JIRAIssue(self, params)
        issue.setProject('CS')
        issue.setIssueType('Proactive')
        issue.setPriority(3)
        issue.setReporter('proactive-support')
        issue = self.createIssue(issue.data)

        print "Setting to WFC..."

        if self.live:
            # Set to Wait for Customer
            # (u'761', u'Wait for Customer')
            try:
                self.transition_issue(issue, '761')
            except JIRAError:
                e = sys.exc_info()[0]
                print "JIRApp.createProactiveIssue: ", e

        return issue

    def setLive(self, b):
        """ Lock and load? """
        self.live = b

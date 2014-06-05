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

            if params['issuetype'].lower() == "proactive":
                print "Setting to WFC..."

                try:
                    # (u'761', u'Wait for Customer')
                    self.transition_issue(issue, '761')
                except JIRAError:
                    e = sys.exc_info()[0]
                    print "JIRApp.createIssue: ", e

        else:
            issue.dump()

        return issue

    def setLive(self, b):
        """ Lock and load? """
        self.live = b

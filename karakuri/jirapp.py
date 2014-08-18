import random
import time

from jira.client import JIRA
from jira.resources import Issue as JIRAIssue
from jira.exceptions import JIRAError
from pprint import pprint
from pymongo.errors import PyMongoError


class jirapp(JIRA):
    """ JIRA++ is JIRA+1. Use it to profit. """

    def __init__(self, config, jirametadb, supportdb):
        # By default we sit here and look pretty
        # All talk, no walk
        self.live = False
        # jirameta
        self.jirametadb = jirametadb
        # support
        self.supportdb = supportdb

        # Set random seed
        random.seed(time.localtime())

        opts = {'server': 'https://jira.mongodb.org', "verify": False}
        auth = (config.get('JIRA', 'username'), config.get('JIRA', 'password'))

        JIRA.__init__(self, options=opts, basic_auth=auth)

    def addPublicComment(self, issue, comment):
        """ This method adds a public-facing comment to a JIRA issue """
        # TODO validate comment

        print "Adding public comment..."

        if self.live:
            try:
                return self.add_comment(issue, comment)

            except JIRAError as e:
                raise e

        else:
            self.verbot()

    def addDeveloperComment(self, issue, comment):
        """ This method adds a developer-only comment to a JIRA issue """
        # TODO validate comment

        print "Adding developer-only comment..."

        if self.live:
            try:
                return self.add_comment(issue, comment,
                                        visibility={'type': 'role',
                                                    'value': 'Developers'})

            except JIRAError as e:
                raise e

        else:
            self.verbot()

    def closeIssue(self, issue):
        """ This method closes a JIRA issue """

        print "Closing issue..."

        if self.live:
            try:
                tid = self.getTransitionId(issue, 'Close Issue')

            except Exception as e:
                raise e

            print "Transitioning issue..."

            try:
                # TODO does transition_issue return anything?
                self.transition_issue(issue, tid)
                return True

            except JIRAError as e:
                raise e

        else:
            self.verbot()

    def createIssue(self, fields={}):
        """ This method creates a JIRA issue. Assume fields is in a format that
        can be passed to JIRA.create_issue, i.e. use SupportIssue.getJIRAFields
        """
        # Use createmeta to identify required fields for ticket creation
        if 'project' not in fields or 'issuetype' not in fields:
            raise Exception("project and issuetype required for createmeta")

        coll_createmeta = self.jirametadb.createmeta
        match = {'pkey': fields['project']['key'], 'itname':
                 fields['issuetype']['name']}
        proj = {'required': 1, '_id': 0}

        # required fields for issue creation
        required_fields = None

        print "Getting createmeta data..."

        try:
            doc = coll_createmeta.find_one(match, proj)

        except PyMongoError as e:
            raise e

        if doc and 'required' in doc:
            required_fields = doc['required']

        if required_fields is not None:
            # In case there are errors we'll find them all before failing
            raiseexception = False

            for f in required_fields:
                if f not in fields:
                    print "Error: %s required to create %s %s JIRA issue" %\
                        (f, fields['issuetype']['name'],
                         fields['project']['key'])
                    raiseexception = True

            if raiseexception is True:
                raise Exception("jira.createmeta validation failed")

        print "Creating JIRA issue..."

        if self.live:
            try:
                issue = self.create_issue(fields=fields)
                print "Created %s" % issue.key
                return issue.id

            except JIRAError as e:
                raise e

        else:
            pprint(fields)

    def getTransitionId(self, issue, transition):
        """ This method gets the transition id for the given transition name.
        It is dependent on the JIRA issue project and status """
        # TODO validate transition

        # A ticket may undergo several state-changing actions between the time
        # we first queried it in our local db and now. Until we come up with
        # something foolproof we'll query JIRA each time for the ticket status
        # before performing the transition. It's annoying but that's life dude
        if not isinstance(issue, JIRAIssue):
            try:
                issue = self.issue(issue)

            except JIRAError as e:
                raise e

        project = issue.fields.project.key
        status = issue.fields.status.name

        # transition id
        tid = None

        print "Getting %s transition id..." % transition

        try:
            coll_transitions = self.jirametadb.transitions
            match = {'pkey': project, 'sname': status, 'tname': transition}
            proj = {'tid': 1, '_id': 0}
            doc = coll_transitions.find_one(match, proj)
            print "Success!"

        except PyMongoError as e:
            raise e

        if doc and 'tid' in doc:
            tid = doc['tid']

        if tid is None:
            print "Error: unable to locate %s transition" % transition
            raise Exception("invalid transition")

        return tid

    def resolveIssue(self, issue, resolution):
        """ This method resolves a JIRA issue with the given resolution """
        # TODO fetch and cache results of jira.resolutions() elsewhere
        res_map = {'Fixed': '1',
                   "Won't Fix": '2',
                   'Duplicate': '3',
                   'Incomplete': '4',
                   'Cannot Reproduce': '5',
                   'Works as Designed': '6',
                   'Gone away': '7',
                   'Community Answered': '8',
                   'Done': '9'}

        if resolution in res_map:
            rid = res_map[resolution]
        else:
            raise Exception("%s is not a supported resolution type" %
                            resolution)

        print "Resolving issue..."

        if self.live:
            tid = self.getTransitionId(issue, 'Resolve Issue')

            print "Transitioning issue..."

            try:
                self.transition_issue(issue, tid, resolution={'id': rid})
                print "Success!"
                return True

            except JIRAError as e:
                raise e

        else:
            self.verbot()

    def setLabels(self, issue, labels):
        """ This method sets the labels in a JIRA issue """
        # TODO validate labels is a string that will return [] on split

        print "Setting labels..."

        if self.live:
            try:
                issue.update(labels=labels.split(','))
                print "Success!"
                return True

            except JIRAError as e:
                raise e

        else:
            self.verbot()

    def setLive(self, b):
        """ Lock and load? """
        self.live = b

    def setOwner(self, issue, owner):
        """ This method sets the JIRA issue owner using the Internal Fields
        transition """

        print "Setting owner..."

        if self.live:
            fields = {'customfield_10041': {'name': owner}}
            tid = self.getTransitionId(issue, 'Internal Fields')

            print "Transitioning issue..."

            try:
                self.transition_issue(issue, tid, fields=fields)
                print "Success!"
                return True

            except JIRAError as e:
                raise e

        else:
            self.verbot()

    def wfcIssue(self, issue):
        """ This method sets the status of a ticket to Wait for Customer """

        print "Changing to WFC..."

        if self.live:
            # if issue is already WFC return
            doc = self.supportdb.issues.find_one({'jira.id': issue})

            if doc and doc['jira']['fields']['status']['name'] ==\
                    "Waiting for Customer":
                print "Issue is already WFC!"
                return True

            tid = self.getTransitionId(issue, 'Wait for Customer')

            print "Transitioning issue..."

            try:
                self.transition_issue(issue, tid)
                print "Success!"
                return True

            except JIRAError as e:
                raise e

        else:
            self.verbot()

    def verbot(self):
        """ This method prints out beeps and boops in place of doing
        anything for realz """

        beepboop = ["beep", "boop"]
        nb = random.randint(3, 7)

        utterance = ""
        for i in range(0, nb):
            utterance += beepboop[random.randint(0, 1)]
            if i < (nb-1):
                utterance += " "

        print utterance

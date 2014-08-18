from datetime import datetime
from jira.client import JIRA
from jira.resources import Issue as JIRAIssue
from jira.exceptions import JIRAError
from pprint import pprint
from pymongo.errors import PyMongoError


def log(msg):
    print "[{0}] {1}".format(datetime.now(), msg)


class jirapp(JIRA):
    """ JIRA++ is JIRA+1. Use it to profit. """
    def __init__(self, config, jirametadb, supportdb):
        log("Initializing JIRA++")

        # By default we sit here and look pretty
        # All talk, no walk
        self.live = False
        # jirameta
        self.jirametadb = jirametadb
        # support
        self.supportdb = supportdb

        opts = {'server': 'https://jira.mongodb.org', "verify": False}
        auth = (config.get('JIRA', 'username'), config.get('JIRA', 'password'))

        try:
            JIRA.__init__(self, options=opts, basic_auth=auth)

        except JIRAError as e:
            raise e

    def __getTransitionId(self, issue, transition):
        """ This method gets the transition id for the given transition name.
        It is dependent on the JIRA issue project and status """
        # A ticket may undergo several state-changing actions between the time
        # we first queried it in our local db and now. Until we come up with
        # something foolproof we'll query JIRA each time for the ticket status
        # before performing the transition. It's annoying but that's life dude
        if not isinstance(issue, JIRAIssue):
            try:
                issue = self.issue(issue.key)

            except JIRAError as e:
                raise e

        project = issue.fields.project.key
        status = issue.fields.status.name

        # transition id
        tid = None

        log("Finding '%s' transition id for project:'%s', status:'%s'" % (
              transition, project, status))

        try:
            coll_transitions = self.jirametadb.transitions
            match = {'pkey': project, 'sname': status, 'tname': transition}
            proj = {'tid': 1, '_id': 0}
            doc = coll_transitions.find_one(match, proj)

        except PyMongoError as e:
            raise e

        if doc and 'tid' in doc and doc['tid'] is not None:
            tid = doc['tid']
            log("Found transition id:%s" % tid)

        else:
            log("Transition id not found. Most likely issue is already in the desired state.")

        return tid

    def addPublicComment(self, issue, comment):
        """ This method adds a public-facing comment to a JIRA issue """
        # TODO validate comment
        log("Adding public comment to JIRA %s" % issue.key)

        if self.live:
            try:
                self.add_comment(issue.key, comment)

            except JIRAError as e:
                raise e

        return issue

    def addDeveloperComment(self, issue, comment):
        """ This method adds a developer-only comment to a JIRA issue """
        # TODO validate comment
        log("Adding developer-only comment to JIRA %s" % issue.key)

        if self.live:
            try:
                self.add_comment(issue.key, comment,
                                 visibility={'type': 'role',
                                             'value': 'Developers'})

            except JIRAError as e:
                raise e

        return issue

    def closeIssue(self, issue):
        """ This method closes a JIRA issue """
        log("Closing JIRA %s" % issue.key)

        if self.live:
            tid = self.__getTransitionId(issue, 'Close Issue')

            if tid:
                try:
                    self.transition_issue(issue.key, tid)

                except JIRAError as e:
                    raise e

        return issue

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

        log("Getting createmeta data for project:%s, issuetype:%s" % (
              fields['project']['key'], fields['issuetype']['name']))

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
                    log("Error: %s required to create %s %s JIRA issue" %\
                        (f, fields['issuetype']['name'],
                         fields['project']['key']))
                    raiseexception = True

            if raiseexception is True:
                raise Exception("jira.createmeta validation failed")

        log("Creating JIRA issue...")

        if self.live:
            try:
                issue = self.create_issue(fields=fields)

            except JIRAError as e:
                raise e

            log("Created JIRA %s" % issue.key)
            return issue

        else:
            pprint(fields)

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

        log("Resolving JIRA %s" % issue.key)

        if self.live:
            tid = self.__getTransitionId(issue, 'Resolve Issue')

            if tid:
                try:
                    self.transition_issue(issue.key, tid, resolution={'id': rid})

                except JIRAError as e:
                    raise e

        return issue

    def setLabels(self, issue, labels):
        """ This method sets the labels in a JIRA issue """
        # TODO validate labels is a string that will return [] on split
        log("Setting labels in JIRA %s" % issue.key)

        if self.live:
            if not isinstance(issue, JIRAIssue):
                try:
                    issue = self.issue(issue)

                except JIRAError as e:
                    raise e

            try:
                issue.update(labels=labels.split(','))

            except JIRAError as e:
                raise e

        return issue

    def setLive(self, b):
        """ Lock and load? """
        self.live = b

    def setOwner(self, issue, owner):
        """ This method sets the JIRA issue owner using the Internal Fields
        transition """
        log("Setting owner of JIRA %s" % issue.key)

        if self.live:
            fields = {'customfield_10041': {'name': owner}}
            tid = self.__getTransitionId(issue, 'Internal Fields')

            if tid:
                try:
                    self.transition_issue(issue.key, tid, fields=fields)

                except JIRAError as e:
                    raise e

        return issue

    def wfcIssue(self, issue):
        """ This method sets the status of a ticket to Wait for Customer """
        log("Setting JIRA %s to Wait for Customer" % issue.key)

        if self.live:
            tid = self.__getTransitionId(issue, 'Wait for Customer')

            if tid:
                try:
                    self.transition_issue(issue.key, tid)

                except JIRAError as e:
                    raise e

        return issue

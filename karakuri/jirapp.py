import logging
import pymongo

from jira.client import JIRA
from jira.exceptions import JIRAError


class jirapp(JIRA):
    """ JIRA++ is JIRA+1. Use it to profit. """
    def __init__(self, username, password, mongo=None):
        logging.info("Initializing JIRA++")

        # By default we sit here and look pretty
        # All talk, no walk
        self.live = False

        if mongo is not None:
            # jirameta
            self.db_jirameta = mongo.jirameta
        else:
            # TODO propagate this case to draw needed information from JIRA
            # instead of from MongoDB
            # For now just throw an exception
            raise Exception("unable to access jirameta")

        opts = {'server': 'https://jira.mongodb.org', "verify": False}
        auth = (username, password)

        try:
            JIRA.__init__(self, options=opts, basic_auth=auth)
        except JIRAError as e:
            raise e

    def __getTransitionId(self, key, transition):
        """ This method gets the transition id for the given transition name.
        It is dependent on the JIRA issue project and status """
        # A ticket may undergo several state-changing actions between the time
        # we first queried it in our local db and now. Until we come up with
        # something foolproof we'll query JIRA each time for the ticket status
        # before performing the transition. It's annoying but that's life dude
        try:
            issue = self.issue(key)
        except JIRAError as e:
            return {'ok': False, 'payload': e}

        project = issue.fields.project.key
        status = issue.fields.status.name

        # transition id
        tid = None

        logging.debug("Finding %s transition id for project:'%s', "
                      "status:'%s'" % (transition, project, status))

        try:
            coll_transitions = self.db_jirameta.transitions
            match = {'pkey': project, 'sname': status, 'tname': transition}
            proj = {'tid': 1, '_id': 0}
            doc = coll_transitions.find_one(match, proj)
        except pymongo.errors.PyMongoError as e:
            return {'ok': False, 'payload': e}

        if doc and 'tid' in doc and doc['tid'] is not None:
            tid = doc['tid']
            logging.info("Found transition id:%s" % tid)
        else:
            logging.warning("Transition id not found. Most likely issue is "
                            "already in the desired state.")

        return {'ok': True, 'payload': tid}

    def addPublicComment(self, key, comment):
        """ This method adds a public-facing comment to a JIRA issue """
        # TODO validate comment
        logging.info("Adding public comment to %s" % key)

        if self.live:
            try:
                self.add_comment(key, comment)
            except JIRAError as e:
                return {'ok': False, 'payload': e}

        return {'ok': True, 'payload': True}

    def addDeveloperComment(self, key, comment):
        """ This method adds a developer-only comment to a JIRA issue """
        # TODO validate comment
        logging.info("Adding developer-only comment to %s" % key)

        if self.live:
            try:
                self.add_comment(key, comment, visibility={'type': 'role',
                                 'value': 'Developers'})
            except JIRAError as e:
                return {'ok': False, 'payload': e}

        return {'ok': True, 'payload': True}

    def closeIssue(self, key):
        """ This method closes a JIRA issue """
        logging.info("Closing %s" % key)

        if self.live:
            tid = self.__getTransitionId(key, 'Close Issue')
            if tid:
                try:
                    self.transition_issue(key, tid)
                except JIRAError as e:
                    return {'ok': False, 'payload': e}

        return {'ok': True, 'payload': True}

    def createIssue(self, fields={}):
        """ This method creates a JIRA issue. Assume fields is in a format that
        can be passed to JIRA.create_issue, i.e. use SupportIssue.getJIRAFields
        """
        # Use createmeta to identify required fields for ticket creation
        if 'project' not in fields or 'issuetype' not in fields:
            return {'ok': False, 'payload': 'project and issuetype required '
                                            'for createmeta'}

        coll_createmeta = self.db_jirameta.createmeta

        match = {'pkey': fields['project']['key'], 'itname':
                 fields['issuetype']['name']}
        proj = {'required': 1, '_id': 0}

        # required fields for issue creation
        required_fields = None

        logging.info("Getting createmeta data for project:%s, issuetype:%s" % (
                     fields['project']['key'], fields['issuetype']['name']))

        try:
            doc = coll_createmeta.find_one(match, proj)
        except pymongo.errors.PyMongoError as e:
            return {'ok': False, 'payload': e}

        if doc and 'required' in doc:
            required_fields = doc['required']

        if required_fields is not None:
            for f in required_fields:
                if f not in fields:
                    message = "%s required to create JIRA issue of type '%s' "\
                              "in project '%s'" % (f,
                                                   fields['issuetype']['name'],
                                                   fields['project']['key'])
                    logging.warning(message)
                    return {'ok': False, 'payload': message}

        logging.info("Creating JIRA issue...")

        if self.live:
            try:
                issue = self.create_issue(fields=fields)
                logging.info("Created %s" % issue.key)
                return {'ok': True, 'payload': issue.key}
            except JIRAError as e:
                return {'ok': False, 'payload': e}
        else:
            logging.debug(fields)
            return {'ok': True, 'payload': 'CS-XXXXX'}

    def resolveIssue(self, key, resolution):
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
            return {'ok': False, 'payload': "%s is not a supported resolution "
                                            "type" % resolution}

        logging.info("Resolving %s" % key)

        if self.live:
            tid = self.__getTransitionId(key, 'Resolve Issue')
            if tid:
                try:
                    self.transition_issue(key, tid, resolution={'id': rid})
                except JIRAError as e:
                    return {'ok': False, 'payload': e}

        return {'ok': True, 'payload': True}

    def setLabels(self, key, labels):
        """ This method sets the labels in a JIRA issue """
        # TODO validate labels is a string that will return [] on split
        logging.info("Setting labels in %s" % key)

        try:
            issue = self.issue(key)
        except JIRAError as e:
            return {'ok': False, 'payload': e}

        try:
            issue.update(labels=labels.split(','))
        except JIRAError as e:
            return {'ok': False, 'payload': e}

        return {'ok': True, 'payload': True}

    def setLive(self, b):
        """ Lock and load? """
        self.live = b

    def setOwner(self, key, owner):
        """ This method sets the JIRA issue owner using the Internal Fields
        transition """
        logging.info("Setting owner of %s" % key)

        if self.live:
            fields = {'customfield_10041': {'name': owner}}
            tid = self.__getTransitionId(key, 'Internal Fields')

            if tid:
                try:
                    self.transition_issue(key, tid, fields=fields)
                except JIRAError as e:
                    return {'ok': False, 'payload': e}

        return {'ok': True, 'payload': True}

    def wfcIssue(self, key):
        """ This method sets the status of a ticket to Wait for Customer """
        logging.info("Setting %s to Wait for Customer" % key)

        if self.live:
            tid = self.__getTransitionId(key, 'Wait for Customer')
            if tid:
                try:
                    self.transition_issue(key, tid)
                except JIRAError as e:
                    return {'ok': False, 'payload': e}

        return {'ok': True, 'payload': True}

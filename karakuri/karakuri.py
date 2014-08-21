import json
import logging
import os
import pymongo

from bson import ObjectId
from datetime import datetime, timedelta
from jirapp import jirapp
from pprint import pprint
from supportissue import SupportIssue
from ConfigParser import RawConfigParser


class karakuri:
    """ An automaton: http://en.wikipedia.org/wiki/Karakuri_ningy%C5%8D """
    def __init__(self, config, mongodb):
        logging.basicConfig(format='[%(asctime)s] %(message)s',
                            level=logging.INFO)
        logging.info("Initializing Karakuri")

        # TODO add command line arguments

        self.ticketer = None
        self.live = False
        self.verbose = False

        if self.verbose:
            for s in config.sections():
                # TODO why doesn't this work?
                logging.debug("%s", s)
                logging.debug(pprint(config.items(s)))

        # Initialize databases and collections
        self.db_jirameta = mongodb.jirameta
        self.db_support = mongodb.support
        self.db_karakuri = mongodb.karakuri
        self.coll_issues = self.db_support.issues

        self.coll_workflows = self.db_karakuri.workflows
        self.coll_log = self.db_karakuri.log
        self.coll_queue = self.db_karakuri.queue

        # TODO extract JIRA specific config and pass to JIRA++
        # Initialize JIRA++
        self.jirapp = jirapp(config, self.db_jirameta, self.db_support)
        self.jirapp.setLive(self.live)

        # Set the ticketer. There can be only one:
        # https://www.youtube.com/watch?v=sqcLjcSloXs
        self.setTicketer(self.jirapp)

    def find_and_modify(self, collection, match, updoc):
        res = None

        try:
            res = collection.find_and_modify(match, updoc)
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)

        return res

    def find_one(self, collection, match):
        res = None

        try:
            res = collection.find_one(match)
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)

        return res

    def queue_find_and_modify(self, match, updoc):
        if "$set" in updoc:
            updoc["$set"]['t'] = datetime.utcnow()
        else:
            updoc["$set"] = {'t': datetime.utcnow()}

        return self.find_and_modify(self.coll_queue, match, updoc)

    def approveQueue(self, qid):
        match = {'_id': ObjectId(qid)}
        updoc = {"$set": {'approved': True}}
        return self.queue_find_and_modify(match, updoc)

    def removeQueue(self, qid):
        # documents cannot actually be removed from a capped collection
        # set wakeDate to the end of time
        wakeDate = datetime.max

        match = {'_id': ObjectId(qid)}
        updoc = {"$set": {'start': wakeDate}}
        return self.queue_find_and_modify(match, updoc)

    def sleepQueue(self, qid, seconds):
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            difference = timedelta(seconds=seconds)
            wakeDate = now + difference

        match = {'_id': ObjectId(qid)}
        updoc = {"$set": {'start': wakeDate}}
        return self.queue_find_and_modify(match, updoc)

    def wakeQueue(self, qid):
        match = {'_id': ObjectId(qid)}
        updoc = {"$set": {'start': datetime.utcnow()}}
        return self.queue_find_and_modify(match, updoc)

    def sleepIssue(self, iid, seconds):
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            difference = timedelta(seconds=seconds)
            wakeDate = now + difference

        match = {'_id': ObjectId(iid)}
        updoc = {"$set": {'karakuri.sleep': wakeDate}}
        return self.find_and_modify(self.coll_issues, match, updoc)

    def wakeIssue(self, iid):
        match = {'_id': ObjectId(iid)}
        updoc = {"$unset": {'karakuri.sleep': ""}}
        return self.find_and_modify(self.coll_issues, match, updoc)

    def getListOfQueueDocuments(self):
        curs_queue = self.coll_queue.find()
        return [q for q in curs_queue]

    def getQueueDocument(self, queueId):
        """ Return the specified queue document """
        if not isinstance(queueId, ObjectId):
            queueId = ObjectId(queueId)

        if self.verbose:
            logging.info("getQueueDocument('%s')", queueId)

        doc = self.find_one(self.coll_queue, {'_id': queueId})

        if doc:
            return doc

        logging.warning("queue document %s !found", queueId)
        return None

    def getSupportIssue(self, issueId):
        """ Return a SupportIssue for the given issueId """
        if not isinstance(issueId, ObjectId):
            issueId = ObjectId(issueId)

        if self.verbose:
            logging.info("getSupportIssue('%s')", issueId)

        doc = self.find_one(self.coll_issues, {'_id': issueId})

        if doc:
            issue = SupportIssue()
            issue.fromDoc(doc)
            return issue

        logging.warning("issue %s !found", issueId)
        return None

    def log(self, issueId, workflowName, action, success):
        logging.info("log('%s', '%s', '%s', %s)", issueId, workflowName,
                     action, success)

        lid = ObjectId()

        doc = {'_id': lid, 'iid': issueId, 'workflow': workflowName,
               'action': action, 'p': success}

        try:
            self.coll_log.insert(doc)
        except pymongo.errors.PyMongoError as e:
            raise e

        return lid

    def queueWorkflow(self, issueId, workflowName):
        logging.info("queue('%s', '%s')", issueId, workflowName)

        # don't queue a workflow that is already queued
        match = {'iid': issueId, 'workflow': workflowName}
        if self.coll_queue.find(match).count() != 0:
            logging.info("%s already queued for issue '%s'", workflowName,
                         issueId)
            self.log(issueId, workflowName, 'queue', False)
            return None

        now = datetime.utcnow()
        doc = {'iid': issueId, 'workflow': workflowName, 'approved': False,
               'done': False, 'inProg': False, 't': now, 'start': now}

        try:
            self.coll_queue.insert(doc)
        except pymongo.errors.PyMongoError as e:
            raise e

        self.log(issueId, workflowName, 'queue', True)

    # TODO rename -> dequeue
    def perform(self, queueId):
        logging.info("perform('%s')", queueId)

        match = {'_id': queueId}
        updoc = {"$set": {'inProg': True, 't': datetime.utcnow()}}

        try:
            doc = self.coll_queue.find_and_modify(match, updoc)
        except pymongo.errors.PyMongoError as e:
            raise e

        if doc and 'workflow' in doc and doc['workflow']:
            if self.performWorkflow(doc['iid'], doc['workflow']):
                updoc = {"$set": {'done': True, 'inProg': False,
                         't': datetime.utcnow()}}

                try:
                    self.coll_queue.find_and_modify(match, updoc)
                except pymongo.errors.PyMongoError as e:
                    raise e

    def performWorkflow(self, issueId, workflowName):
        """ Perform the proposed workflow for the given issue """
        logging.info("performWorkflow('%s', '%s')", issueId, workflowName)

        # validate that this is still worth running
        if self.validate(issueId, workflowName):
            self.log(issueId, workflowName, 'validate', True)
        else:
            logging.info("Issue does not satisfy workflow requirements, "
                         "will !perform")
            self.log(issueId, workflowName, 'validate', False)

        issue = self.getSupportIssue(issueId)
        if not issue:
            raise Exception("unable to get SupportIssue for issue %s" %
                            issueId)

        workflow = self.find_one(self.coll_workflows, {'name': workflowName})

        if not workflow:
            raise Exception("workflow %s is !defined" % workflow['name'])

        # so far so good
        success = True

        for action in workflow['actions']:
            # ensure action is defined for this ticketing system
            if not hasattr(self.ticketer, action['name']):
                raise Exception("%s is not a supported action" %
                                action['name'])

            args = []

            if 'args' in action:
                args = list(action['args'])
            else:
                args = []

            # first argument is ticketer-dependent
            # JIRA takes a JIRA-key
            args.insert(0, issue.jiraKey)

            # for the sake of logging reduce string arguments
            # to 50 characters and replace \n with \\n
            argString = (', '.join('"' + arg[:50].replace('\n',
                         '\\n') + '"' for arg in args))
            logging.info("Calling %s(%s)" % (action['name'], argString))

            if self.live:
                f = getattr(self.ticketer, action['name'])
                # expand list to function arguments
                r = f(*args)
            else:
                # simulate success
                r = True

            if not r:
                success = False
                break

        lid = self.log(issue.id, workflow['name'], 'perform', success)

        if success:
            match = {'_id': issue.id}
            updoc = {'$set': {'updated': datetime.utcnow()},
                     '$push': {'karakuri.workflows_performed':
                               {'name': workflow['name'], 'lid': lid}}}

            try:
                self.coll_issues.update(match, updoc)
            except pymongo.errors.PyMongoError as e:
                raise e

        return success

    def performAll(self):
        """ Perform all approved workflows """
        logging.info("performAll()")

        match = {'done': False, 'inProg': False, 'approved': True}

        try:
            curs_queue = self.coll_queue.find(match)
        except pymongo.errors.PyMongoError as e:
            raise e

        for i in curs_queue:
            self.perform(i['_id'])

    def validate(self, issueId, workflowName):
        """ Verify that the given issue satisfies the requirements to run the
        specified workflow """
        logging.info("validate('%s', '%s')", issueId, workflowName)

        workflow = self.find_one(self.coll_workflows, {'name': workflowName})

        if not workflow:
            raise Exception("workflow %s is !defined" % workflowName)

        query_string = workflow['query_string']
        match = json.loads(query_string)

        # has workflow already been performed for this issue?
        # if so we're probably in the middle of a sequence of workflows
        if "$and" not in match:
            match["$and"] = []
        match["$and"].append({'karakuri.workflows_performed.name': {"$ne":
                              workflow['name']}})

        if 'prereqs' in workflow:
            # require each prerequisite has been met
            prereqs = workflow['prereqs']

            for prereq in prereqs:
                match['$and'].append({'karakuri.workflows_performed.name':
                                     prereq})

        # finally, the specified issue must return in the query!
        match['_id'] = issueId

        if self.verbose:
            logging.debug(pprint(match))

        if self.coll_issues.find(match).count() == 1:
            logging.info("workflow validated")
            return True
        else:
            logging.info("workflow failed validation")
            return False

    def findAndQueue(self):
        logging.info("findAndQueue()")

        try:
            curs_workflows = self.coll_workflows.find()
        except pymongo.errors.PyMongoError as e:
            raise e

        for workflow in curs_workflows:
            logging.info("Considering %s workflow" % workflow['name'])

            query_string = workflow['query_string']
            match = json.loads(query_string)

            # do not include issues for which the given workflow
            # has already been performed!
            if "$and" not in match:
                match["$and"] = []
            match["$and"].append({'karakuri.workflows_performed.name': {"$ne":
                                  workflow['name']}})

            if 'prereqs' in workflow:
                # require each prerequisite has been met
                prereqs = workflow['prereqs']
                for prereq in prereqs:
                    match['$and'].append({'karakuri.workflows_performed.name':
                                          prereq})

            # find 'em and get 'er done!
            try:
                curs_issues = self.coll_issues.find(match)
            except pymongo.errors.PyMongoError as e:
                raise e

            for i in curs_issues:
                issue = SupportIssue()
                issue.fromDoc(i)

                # we only support JIRA at the moment
                if not issue.hasJIRA():
                    logging.info("Skipping unsupported ticketing type!")
                    continue

                # check for Karakuri actions
                if not issue.isActive():
                    logging.info("Skipping %s as it is not active" % issue.key)
                    continue

                # require time_elapsed has passed since last public comment
                # use 'updated' as comment could have been created dev-only
                lastPublicComment = issue.lastXGenPublicComment

                # if no public comments, use issue updated
                if lastPublicComment is None:
                    lastDate = issue.updated
                else:
                    # TODO get updated, not just created :(
                    lastDate = lastPublicComment['created']

                # it's possible that we got here after a previous workflow
                # and before our jira was updated to reflect that
                if issue.hasKarakuri():
                    # TODO create getters for these
                    if 'updated' in issue.doc['karakuri']:
                        lastKarakuri = issue.doc['karakuri']['updated']
                        if lastKarakuri > lastDate:
                            lastDate = lastKarakuri

                # require that the issue have a company?
                # company = issue.company
                # require that the customer has never before commented?
                # lcc = issue.lastCustomerComment

                # has enough time elapsed?
                time_elapsed = timedelta(seconds=workflow['time_elapsed'])
                # in UTC please!
                now = datetime.utcnow()

                if lastDate + time_elapsed < now:
                    self.queueWorkflow(issue.id, workflow['name'])

    def setTicketer(self, ticketer):
        self.ticketer = ticketer


if __name__ == "__main__":
    #
    # Parse command line options
    #

    #
    # Parse configuration file
    #

    config = RawConfigParser()
    config.read(os.getcwd() + "/karakuri.cfg")  # + options.config)

    # Initialize MongoDB
    # TODO configuration passed to MongoClient
    mongodb = pymongo.MongoClient()

    kk = karakuri(config, mongodb)
    kk.findAndQueue()
    kk.performAll()

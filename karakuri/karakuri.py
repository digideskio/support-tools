#!/usr/bin/env python

import argparse
import bottle
import bson
import bson.json_util
import logging
import os
import pymongo
import sys

from configparser import ConfigParser
from datetime import datetime, timedelta
from jirapp import jirapp
from supportissue import SupportIssue


class karakuri:
    """ An automaton: http://en.wikipedia.org/wiki/Karakuri_ningy%C5%8D """
    def __init__(self, args):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

        # log what your momma gave ya
        self.logger = logging.getLogger("logger")
        self.logger.setLevel(self.args['log_level'])
        fh = logging.FileHandler(self.args['log'])
        fh.setLevel(self.args['log_level'])
        formatter = logging.Formatter('%(asctime)s - %(module)s - '
                                      '%(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.info("waking karakuri...")

        # output args for debugging
        self.logger.debug("parsed args:")
        for arg in self.args:
            self.logger.debug("%s %s" % (arg, self.args[arg]))

        # will the real __init__ please stand up, please stand up...
        self.issuer = None
        self.live = self.args['live']

        # initialize dbs and collections
        # TODO try except this
        self.mongo = pymongo.MongoClient(self.args['mongo_host'],
                                         self.args['mongo_port'])
        self.coll_issues = self.mongo.support.issues
        self.coll_workflows = self.mongo.karakuri.workflows
        self.coll_log = self.mongo.karakuri.log
        self.coll_queue = self.mongo.karakuri.queue

    def approveTicket(self, tid):
        """ Approve the ticket for processing """
        self.logger.debug("approveTicket(%s)", tid)
        updoc = {"$set": {'approved': True}}
        return self.updateTicket(tid, updoc)

    def _buildValidateQuery(self, workflow, iid=None):
        """ Return a MongoDB query that accounts for the workflow prerequisites
        """
        self.logger.debug("_buildValidateQuery(%s,%s)", workflow['name'], iid)
        query_string = workflow['query_string']
        match = bson.json_util.loads(query_string)

        # issue must exist!
        match['deleted'] = False

        # do not include issues for which the given workflow
        # has already been performed!
        # TODO this is not what we want to do in the end, why not
        # run the same workflow twice?
        # perhaps we need a new concept, workflow chains, to
        # mark the end of the line
        if "$and" not in match:
            match["$and"] = []
        match["$and"].append({'karakuri.workflows_performed.name': {"$ne":
                              workflow['name']}})

        # time elapsed since issue last updated
        time_elapsed = timedelta(seconds=workflow['time_elapsed'])
        # in UTC please!
        now = datetime.utcnow()
        start = now - time_elapsed
        match["$and"].append({'updated': {"$lte": start}})

        if iid is not None:
            # the specified issue must return in the query!
            res = self.getObjectId(iid)
            if not res['ok']:
                return None
            iid = res['payload']
            match['_id'] = iid

        if 'prereqs' in workflow:
            # require that each prerequisite has been met
            prereqs = workflow['prereqs']
            for prereq in prereqs:
                # time elapsed since prereq logged
                time_elapsed = timedelta(seconds=prereq['time_elapsed'])
                start = now - time_elapsed
                start = bson.ObjectId.from_datetime(start)
                match['$and'].append({'karakuri.workflows_performed':
                                     {"$elemMatch": {'name': prereq['name'],
                                                     'lid': {"$lte": start}}}})

        return match

    def disapproveTicket(self, tid):
        """ Disapprove the ticket for processing """
        self.logger.debug("disapproveTicket(%s)", tid)
        updoc = {"$set": {'approved': False}}
        return self.updateTicket(tid, updoc)

    def find_and_modify(self, collection, match, updoc):
        """ Wrapper for find_and_modify that handles exceptions """
        self.logger.debug("find_and_modify(%s,%s,%s)", collection, match,
                          updoc)
        try:
            # return the 'new' updated document
            doc = collection.find_and_modify(match, updoc, new=True)
            return {'ok': True, 'payload': doc}
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

    def find_and_modify_issue(self, match, updoc):
        """ find_and_modify for support.issues that automatically updates the
        'updated' timestamp """
        self.logger.debug("find_and_modify_issue(%s,%s)", match, updoc)
        if "$set" in updoc:
            updoc["$set"]['updated'] = datetime.utcnow()
        else:
            updoc["$set"] = {'updated': datetime.utcnow()}
        return self.find_and_modify(self.coll_issues, match, updoc)

    def find_and_modify_ticket(self, match, updoc):
        """ find_and_modify for karakuri.queue that automatically updates the
        't' timestamp """
        self.logger.debug("find_and_modify_ticket(%s,%s)", match, updoc)
        if "$set" in updoc:
            updoc["$set"]['t'] = datetime.utcnow()
        else:
            updoc["$set"] = {'t': datetime.utcnow()}
        return self.find_and_modify(self.coll_queue, match, updoc)

    def find_one(self, collection, match):
        """ Wrapper for find_one that handles exceptions """
        self.logger.debug("find_one(%s,%s)", collection, match)
        try:
            doc = collection.find_one(match)
            return {'ok': True, 'payload': doc}
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

    def findWorkflowTickets(self, workflowNameORworkflow):
        """ Find and queue new tickets that satisfy the workflow """
        self.logger.debug("findWorkflowTickets('%s')", workflowNameORworkflow)
        if isinstance(workflowNameORworkflow, dict):
            workflow = workflowNameORworkflow
        else:
            res = self.getWorkflow(workflowNameORworkflow)
            if not res['ok']:
                return res
            workflow = res['payload']
        self.logger.info("Finding tickets for workflow '%s'", workflow['name'])

        match = self._buildValidateQuery(workflow)

        # find 'em and get 'er done!
        try:
            curs_issues = self.coll_issues.find(match)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        res = True
        tickets = []
        message = ""
        for i in curs_issues:
            issue = SupportIssue()
            issue.fromDoc(i)

            # we only support JIRA at the moment
            if not issue.hasJIRA():
                self.logger.warning("Skipping unsupported ticketing type!")
                continue

            # check for karakuri sleepy time
            if not issue.isActive():
                self.logger.info("Skipping %s as it is not active" % issue.key)
                continue

            _res = self.queueTicket(issue.id, workflow['name'])
            res &= _res['ok']
            if _res['ok']:
                tickets.append(_res['payload'])
            else:
                # We will return a potentially multi-line message
                # of workflow failures
                if message != "":
                    message += "\n"
                message += _res['payload']

        if res:
            payload = tickets
        else:
            payload = message
        return {'ok': res, 'payload': payload}

    def findTickets(self):
        """ Find and queue new tickets """
        self.logger.debug("findTickets()")

        res = self.getListOfWorkflows()
        if not res['ok']:
            return res
        workflows = res['payload']

        res = True
        tickets = []
        message = ""
        for workflow in workflows:
            _res = self.findWorkflowTickets(workflow)
            res &= _res['ok']
            if _res['ok']:
                tickets += _res['payload']
            else:
                # We will return a potentially multi-line message
                # of workflow failures
                if message != "":
                    message += "\n"
                message += _res['payload']

        if res:
            payload = tickets
        else:
            payload = message
        return {'ok': res, 'payload': payload}

    def forListOfTicketIds(self, action, tids, **kwargs):
        """ Perform the given action for the specified tickets """
        self.logger.debug("forListOfTicketIds(%s,%s)", action, tids)
        res = True
        tickets = []
        message = ""
        # Note that we will not exit on action failure. All tickets will get
        # a shot at the action ;)
        for tid in tids:
            _res = action(tid, **kwargs)
            res &= _res['ok']
            if _res['ok']:
                # In the case that res == True, this is part of the payload
                # of 'tickets' delivered
                tickets.append(_res['payload'])
            else:
                # Otherwise, we will return a potentially multi-line message
                # of action-tid failures
                if message != "":
                    message += "\n"
                message += "action '%s' failed for ticket '%s'" % (action, tid)

        # Again, we return False for a single failure, regardless of how many
        # actions completed successfully
        if res:
            payload = tickets
        else:
            payload = message
        return {'ok': res, 'payload': payload}

    def getListOfTicketIds(self, match={}):
        self.logger.debug("getListOfTicketIds(%s)", match)
        res = self.getListOfTickets(match, {'_id': 1})
        if res['ok']:
            return {'ok': True, 'payload': [t['_id'] for t in res['payload']]}
        return res

    def getListOfTickets(self, match={}, proj={}):
        self.logger.debug("getListOfTickets(%s,%s)", match, proj)
        try:
            curs_queue = self.coll_queue.find(match, proj).\
                sort('start', pymongo.ASCENDING)
            return {'ok': True, 'payload': [t for t in curs_queue]}
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

    def getListOfReadyTicketIds(self):
        self.logger.debug("getListOfReadyTicketIds()")
        match = {'active': True, 'done': False, 'inProg': False}
        return self.getListOfTicketIds(match)

    def getListOfReadyWorkflowTicketIds(self, name):
        self.logger.debug("getListOfReadyWorkflowTicketIds(%s)", name)
        match = {'active': True, 'done': False, 'inProg': False,
                 'workflow': name}
        return self.getListOfTicketIds(match)

    def getListOfWorkflows(self):
        self.logger.debug("getListOfWorkflows()")
        try:
            # TODO add sort
            curs_workflows = self.coll_workflows.find()
            return {'ok': True, 'payload': [w for w in curs_workflows]}
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

    def getSupportIssue(self, iid):
        """ Return a SupportIssue for the given iid """
        self.logger.debug("getSupportIssue(%s)", iid)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']

        try:
            res = self.find_one(self.coll_issues, {'_id': iid})
            if not res['ok']:
                return res
            doc = res['payload']
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        # TODO verify that find_one returns None for null
        # and modify conditional to reflect that
        if doc:
            issue = SupportIssue()
            issue.fromDoc(doc)
            return {'ok': True, 'payload': issue}

        message = "issue '%s' not found" % iid
        self.logger.warning(message)
        return {'ok': False, 'payload': message}

    def getTicket(self, tid):
        """ Return the specified ticket """
        self.logger.debug("getTicket(%s)", tid)
        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']

        res = self.find_one(self.coll_queue, {'_id': tid})
        if not res['ok']:
            return res
        ticket = res['payload']

        if ticket is not None:
            return {'ok': True, 'payload': ticket}

        message = "ticket '%s' not found" % tid
        self.logger.warning(message)
        return {'ok': False, 'payload': message}

    def getWorkflow(self, workflowName):
        """ Return the specified workflow """
        self.logger.debug("getWorkflow(%s)", workflowName)
        res = self.find_one(self.coll_workflows, {'name': workflowName})
        if not res['ok']:
            return res
        workflow = res['payload']

        if workflow is not None:
            return {'ok': True, 'payload': workflow}

        message = "workflow '%s' not found!" % workflowName
        self.logger.warning(message)
        return {'ok': False, 'payload': message}

    # TODO move to an external library?
    def getObjectId(self, id):
        """ Return an ObjectId for the given id """
        self.logger.debug("getObjectId(%s)", id)
        if not isinstance(id, bson.ObjectId):
            try:
                id = bson.ObjectId(id)
            except Exception as e:
                self.logger.error(e)
                return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': id}

    def _log(self, iid, workflowName, action, success):
        """ Log to karakuri.log <-- that's a collection! """
        self.logger.debug("log(%s,%s,%s,%s)", iid, workflowName, action,
                          success)

        res = self.getObjectId(iid)
        if not res['ok']:
            return None
        iid = res['payload']

        lid = bson.ObjectId()

        log = {'_id': lid, 'iid': iid, 'workflow': workflowName,
               'action': action, 'p': success}

        try:
            self.coll_log.insert(log)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            # TODO write to file on disk instead

        return lid

    def _performAction(self, action):
        """ Do it like they do on the discovery channel """
        self.logger.debug("_performAction(%s)", action['name'])

        # action must be defined for this issuing system
        if not hasattr(self.issuer, action['name']):
            message = "'%s' is not a supported action" % action['name']
            self.logger.exception(message)
            return {'ok': False, 'payload': message}

        args = list(action['args'])

        # for the sake of logging reduce string arguments
        # to 50 characters and replace \n with \\n
        argString = (', '.join('"' + arg[:50].replace('\n',
                     '\\n') + '"' for arg in args))
        self.logger.info("%s(%s)", action['name'], argString)

        if self.live:
            method = getattr(self.issuer, action['name'])
            # expand list to function arguments
            res = method(*args)
        else:
            # simulate success
            res = True

        return res

    def performWorkflow(self, iid, workflowName):
        """ Perform the specified workflow for the given issue """
        self.logger.debug("performWorkflow(%s,%s)", iid, workflowName)
        res = self.getObjectId(iid)
        if not res['ok']:
            self._log(iid, workflowName, 'perform', False)
            return res
        iid = res['payload']

        res = self.getSupportIssue(iid)
        if not res['ok']:
            self._log(iid, workflowName, 'perform', False)
            return res
        issue = res['payload']

        self.logger.info("that is %s, mind you", issue.key)

        res = self.getWorkflow(workflowName)
        if not res['ok']:
            self._log(iid, workflowName, 'perform', False)
            return res
        workflow = res['payload']

        if workflow is None:
            message = "unable to get workflow '%s'" % workflowName
            self.logger.exception(message)
            self._log(iid, workflowName, 'perform', False)
            return {'ok': False, 'payload': message}

        # validate that this is still worth running
        # TODO add validate to api
        res = self.validate(issue, workflow)
        self._log(iid, workflowName, 'validate', res)

        if not res:
            message = "failed to validate workflow, will not perform"
            self.logger.info(message)
            self._log(iid, workflowName, 'perform', False)
            return {'ok': False, 'payload': message}

        # so far so good
        success = True

        for action in workflow['actions']:
            # first argument is issuer-dependent
            # JIRA takes a key
            if 'args' in action:
                action['args'].insert(0, issue.key)
            else:
                action['args'] = [issue.key]

            res = self._performAction(action)
            self._log(iid, workflowName, action['name'], res)

            if not res:
                success = False
                break

        lid = self._log(iid, workflowName, 'perform', success)

        if success:
            if self.live:
                match = {'_id': iid}
                updoc = {'$push': {'karakuri.workflows_performed':
                                   {'name': workflowName, 'lid': lid}}}
                res = self.find_and_modify_issue(match, updoc)
                if not res['ok'] or res['payload'] is None:
                    message = "unable to record workflow '%s' in issue '%s'"\
                        % (workflowName, iid)
                    self.logger.exception(message)
                    self._log(iid, workflowName, 'record', False)
                    return {'ok': False, 'payload': message}

                self._log(iid, workflowName, 'record', True)

        return {'ok': True, 'payload': None}

    def processTicket(self, tid):
        """ Process the specified ticket """
        self.logger.debug("processTicket(%s)", tid)
        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']

        match = {'_id': tid, 'active': True, 'done': False, 'inProg': False,
                 'approved': True}
        updoc = {"$set": {'inProg': True}}
        res = self.find_and_modify_ticket(match, updoc)
        if not res['ok']:
            return res
        ticket = res['payload']

        if ticket is None:
            # most likely the ticket hasn't been approved
            message = "unable to put ticket '%s' in to progress" % tid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}

        res = self.performWorkflow(ticket['iid'], ticket['workflow'])
        if not res['ok']:
            return res
        res = bool(res['payload'])

        match = {'_id': tid}
        updoc = {"$set": {'done': res, 'inProg': False}}
        res = self.find_and_modify_ticket(match, updoc)
        if not res['ok']:
            return res
        ticket = res['payload']

        if ticket is None:
            message = "unable to take ticket %s out of progress" % tid
            self.logger.exception(message)
            return {'ok': False, 'payload': message}

        return {'ok': True, 'payload': ticket}

    def queueTicket(self, iid, workflowName):
        """ Create a ticket for the given issue and workflow """
        self.logger.info("queueTicket(%s,%s)", iid, workflowName)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']

        # don't queue a ticket that is already queued
        match = {'iid': iid, 'workflow': workflowName, 'active': True,
                 'done': False}
        if self.coll_queue.find(match).count() != 0:
            message = "workflow '%s' already queued for issue '%s'" %\
                (workflowName, iid)
            self.logger.info(message)
            self._log(iid, workflowName, 'queue', False)
            return {'ok': False, 'payload': message}

        now = datetime.utcnow()
        ticket = {'iid': iid, 'workflow': workflowName, 'approved': False,
                  'done': False, 'inProg': False, 't': now, 'start': now,
                  'active': True}

        try:
            self.coll_queue.insert(ticket)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            self._log(iid, workflowName, 'queue', False)
            return {'ok': False, 'payload': e}

        self._log(iid, workflowName, 'queue', True)

        return {'ok': True, 'payload': ticket}

    def removeTicket(self, tid):
        """ Remove the ticket from the queue """
        self.logger.debug("removeTicket(%s)", tid)
        updoc = {"$set": {'active': False}}
        return self.updateTicket(tid, updoc)

    def setIssuer(self, issuer):
        """ Set issue tracking system """
        self.issuer = issuer

    def sleepIssue(self, iid, seconds):
        """ Sleep the issue """
        self.logger.debug("sleepIssue(%s)", iid)
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            diff = timedelta(seconds=seconds)
            wakeDate = now + diff

        updoc = {"$set": {'karakuri.sleep': wakeDate}}
        return self.updateIssue(iid, updoc)

    def sleepTicket(self, tid, seconds):
        """ Sleep the ticket, i.e. assign a wake date """
        self.logger.debug("sleepTicket(%s)", tid)
        seconds = int(seconds)
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            diff = timedelta(seconds=seconds)
            wakeDate = now + diff

        updoc = {"$set": {'start': wakeDate}}
        return self.updateTicket(tid, updoc)

    def updateIssue(self, iid, updoc):
        """ They see me rollin' """
        self.logger.debug("updateIssue(%s,%s)", iid, updoc)

        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']
        match = {'_id': iid}

        res = self.find_and_modify_issue(match, updoc)
        if res['ok']:
            return {'ok': True, 'payload': res['payload']}
        return res

    def updateTicket(self, tid, updoc):
        """ They hatin' """
        self.logger.debug("updateTicket(%s,%s)", tid, updoc)

        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']
        match = {'_id': tid}

        res = self.find_and_modify_ticket(match, updoc)
        if res['ok']:
            return {'ok': True, 'payload': res['payload']}
        return res

    def validate(self, iidORissue, workflowNameORworkflow):
        """ Verify the issue satisfies the requirements of the workflow
        """
        self.logger.debug("validate(%s,%s)", iidORissue,
                          workflowNameORworkflow)

        # handle the multitude of cases
        if isinstance(iidORissue, SupportIssue):
            iid = iidORissue.id
        else:
            iid = iidORissue

        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']

        if isinstance(workflowNameORworkflow, dict):
            workflow = workflowNameORworkflow
        else:
            res = self.getWorkflow(workflowNameORworkflow)
            if not res['ok']:
                return False
            workflow = res['payload']

        self.logger.info("validate('%s', '%s')", iid, workflow['name'])

        match = self._buildValidateQuery(workflow, iid)

        self.logger.debug("%s validate query:", workflow['name'])
        self.logger.debug(match)

        if self.coll_issues.find(match).count() != 0:
            self.logger.info("Workflow validated!")
            return True
        else:
            self.logger.info("Workflow failed validation")
            return False

    def wakeTicket(self, tid):
        """ Wake the ticket, i.e. mark it ready to go """
        self.logger.debug("wakeTicket(%s)", tid)
        updoc = {"$set": {'start': datetime.utcnow()}}
        return self.updateTicket(tid, updoc)

    def wakeIssue(self, iid):
        """ Wake the issue """
        self.logger.debug("wakeIssue(%s)", iid)
        updoc = {"$unset": {'karakuri.sleep': ""}}
        return self.updateIssue(iid, updoc)

    def start(self):
        """ Start the RESTful interface """
        self.logger.debug("start()")
        self.logger.info("karakuri is at REST")

        b = bottle.Bottle()

        # These are the RESTful API endpoints. There are many like it, but
        # these are them
        b.route('/issue', callback=self._issue_list)
        b.route('/issue/<id>', callback=self._issue_get)
        b.route('/issue/<id>/sleep', callback=self._issue_sleep)
        b.route('/issue/<id>/sleep/<seconds:int>', callback=self._issue_sleep)
        b.route('/issue/<id>/wake', callback=self._issue_wake)
        b.route('/queue', callback=self._queue_list)
        b.route('/queue/approve', callback=self._queue_approve)
        b.route('/queue/disapprove', callback=self._queue_disapprove)
        b.route('/queue/find', callback=self._queue_find)
        b.route('/queue/process', callback=self._queue_process)
        b.route('/queue/remove', callback=self._queue_remove)
        b.route('/queue/sleep', callback=self._queue_sleep)
        b.route('/queue/sleep/<seconds:int>', callback=self._queue_sleep)
        b.route('/queue/wake', callback=self._queue_wake)
        # a repete ;)
        b.route('/ticket', callback=self._queue_list)
        b.route('/ticket/<id>', callback=self._ticket_get)
        b.route('/ticket/<id>/approve', callback=self._ticket_approve)
        b.route('/ticket/<id>/disapprove', callback=self._ticket_disapprove)
        b.route('/ticket/<id>/process', callback=self._ticket_process)
        b.route('/ticket/<id>/remove', callback=self._ticket_remove)
        b.route('/ticket/<id>/sleep', callback=self._ticket_sleep)
        b.route('/ticket/<id>/sleep/<seconds:int>',
                callback=self._ticket_sleep)
        b.route('/ticket/<id>/wake', callback=self._ticket_wake)
        b.route('/workflow', callback=self._workflow_list)
        b.route('/workflow/<name>', callback=self._workflow_get)
        b.route('/workflow/<name>/approve', callback=self._workflow_approve)
        b.route('/workflow/<name>/disapprove',
                callback=self._workflow_disapprove)
        b.route('/workflow/<name>/find', callback=self._workflow_find)
        b.route('/workflow/<name>/process', callback=self._workflow_process)
        b.route('/workflow/<name>/remove', callback=self._workflow_remove)
        b.route('/workflow/<name>/sleep', callback=self._workflow_sleep)
        b.route('/workflow/<name>/sleep/<seconds:int>',
                callback=self._workflow_sleep)
        b.route('/workflow/<name>/wake', callback=self._workflow_wake)

        b.run(host='localhost', port=self.args['rest_port'])

    def _success(self, data=None):
        self.logger.debug("_success(%s)", data)
        ret = {'status': 'success', 'data': data}
        return bson.json_util.dumps(ret)

    def _fail(self, data=None):
        self.logger.debug("_fail(%s)", data)
        ret = {'status': 'fail', 'data': data}
        return bson.json_util.dumps(ret)

    def _error(self, message=None):
        self.logger.debug("_error(%s)", message)
        ret = {'status': 'error', 'message': str(message)}
        return bson.json_util.dumps(ret)

    def _issue_list(self):
        """ Return no-way, Jose 404 """
        self.logger.debug("_issue_list()")
        # TODO implement no-way, Jose 404
        return self._fail()

    def _issue_response(self, method, id, **kwargs):
        self.logger.debug("_issue_response(%s,%s)", method, id)
        res = method(id, **kwargs)
        if res['ok']:
            return self._success({'issue': res['payload']})
        return self._error(res['payload'])

    # TODO make new getIssue so you can use _issue_response here instead of
    # getSupportIssue
    def _issue_get(self, id):
        """ Return the issue """
        self.logger.debug("_issue_get(%s)", id)
        res = self.getSupportIssue(id)
        if res['ok']:
            return self._success({'issue': res['payload'].doc})
        return self._error(res['payload'])

    def _issue_sleep(self, id, seconds=sys.maxint):
        """ Sleep the issue. A sleeping issue cannot have tickets queued """
        self.logger.debug("_issue_sleep(%s,%s)", id, seconds)
        return self._issue_response(self.sleepIssue, id, seconds=seconds)

    def _issue_wake(self, id):
        """ Wake the issue, i.e. unsleep it """
        self.logger.debug("_issue_wake(%s)", id)
        return self._issue_response(self.wakeIssue, id)

    def _queue_list(self):
        """ Return a list of all active tickets """
        self.logger.debug("_queue_list()")
        match = {'active': True}
        res = self.getListOfTickets(match)
        if res['ok']:
            return self._success({'tickets': res['payload']})
        return self._error(res['payload'])

    def _queue_find(self):
        """ Find and queue new tickets """
        self.logger.debug("_queue_find()")
        res = self._find()
        if res['ok']:
            return self._success({'tickets': res['payload']})
        return self._error(res['payload'])

    def _queue_response(self, method, **kwargs):
        self.logger.debug("_queue_response(%s)", method)
        res = self.getListOfReadyTicketIds()
        if res['ok']:
            res = self.forListOfTicketIds(method, res['payload'], **kwargs)
            if res['ok']:
                return self._success({'tickets': res['payload']})
        return self._error(res['payload'])

    def _queue_approve(self):
        """ Approve all ready tickets """
        self.logger.debug("_queue_approve()")
        return self._queue_response(self.approveTicket)

    def _queue_disapprove(self):
        """ Disapprove all ready tickets """
        self.logger.debug("_queue_disapprove()")
        return self._queue_response(self.disapproveTicket)

    def _queue_process(self):
        """ Process all ready tickets """
        self.logger.debug("_queue_process()")
        return self._queue_response(self.processTicket)

    def _queue_remove(self):
        """ Remove all ready tickets """
        self.logger.debug("_queue_remove()")
        return self._queue_response(self.removeTicket)

    def _queue_sleep(self, seconds=sys.maxint):
        """ Sleep all ready tickets """
        self.logger.debug("_queue_sleep(%s)", seconds)
        return self._queue_response(self.sleepTicket, seconds=seconds)

    def _queue_wake(self):
        """ Wake all ready tickets """
        self.logger.debug("_queue_wake()")
        return self._queue_response(self.wakeTicket)

    def _ticket_response(self, method, id, **kwargs):
        self.logger.debug("_ticket_response(%s,%s)", method, id)
        res = method(id, **kwargs)
        if res['ok']:
            return self._success({'ticket': res['payload']})
        return self._error(res['payload'])

    def _ticket_get(self, id):
        """ Return the ticket """
        self.logger.debug("_ticket_get(%s)", id)
        return self._ticket_response(self.getTicket, id)

    def _ticket_approve(self, id):
        """ Approve the ticket """
        self.logger.debug("_ticket_approve(%s)", id)
        return self._ticket_response(self.approveTicket, id)

    def _ticket_disapprove(self, id):
        """ Disapprove the ticket """
        self.logger.debug("_ticket_disapprove(%s)", id)
        return self._ticket_response(self.disapproveTicket, id)

    def _ticket_process(self, id):
        """ Process the ticket """
        self.logger.debug("_ticket_process(%s)", id)
        return self._ticket_response(self.processTicket, id)

    def _ticket_remove(self, id):
        """ Remove the ticket """
        self.logger.debug("_ticket_remove(%s)", id)
        return self._ticket_response(self.removeTicket, id)

    def _ticket_sleep(self, id, seconds=sys.maxint):
        """ Sleep the ticket. A sleeping ticket cannot be processed """
        self.logger.debug("_ticket_sleep(%s,%s)", id, seconds)
        return self._ticket_response(self.sleepTicket, id, seconds=seconds)

    def _ticket_wake(self, id):
        """ Wake the ticket, i.e. unsleep it """
        self.logger.debug("_ticket_wake(%s)", id)
        return self._ticket_response(self.wakeTicket, id)

    def _workflow_list(self):
        """ Return a list of workflows """
        self.logger.debug("_workflow_list()")
        res = self.getListOfWorkflows()
        if res['ok']:
            return self._success({'workflows': res['payload']})
        return self._error()

    def _workflow_response(self, method, name, **kwargs):
        self.logger.debug("_workflow_response(%s,%s)", method, name)
        res = self.getListOfReadyWorkflowTicketIds(name)
        if res['ok']:
            res = self.forListOfTicketIds(method, res['payload'], **kwargs)
            if res['ok']:
                return self._success({'workflow': res['payload']})
        return self._error(res['payload'])

    def _workflow_get(self, name):
        """ Return the workflow """
        self.logger.debug("_workflow_get(%s)", name)
        return self._workflow_response(self.getWorkflow, name)

    def _workflow_approve(self, name):
        """ Approve all ready tickets for the workflow """
        self.logger.debug("_workflow_approve(%s)", name)
        return self._workflow_response(self.approveTicket, name)

    def _workflow_disapprove(self, name):
        """ Disapprove all ready tickets for the workflow """
        self.logger.debug("_workflow_disapprove(%s)", name)
        return self._workflow_response(self.disapproveTicket, name)

    def _workflow_find(self, name):
        """ Find and queue new tickets for the workflow """
        self.logger.debug("_workflow_find()")
        tickets = self.findWorkflowTickets(name)
        if tickets is not None:
            return self._success({'tickets': tickets})
        return self._error()

    def _workflow_process(self, name):
        """ Process all ready tickets for the workflow """
        self.logger.debug("_workflow_process(%s)", name)
        return self._workflow_response(self.processTicket, name)

    def _workflow_remove(self, name):
        """ Remove all ready tickets for the workflow """
        self.logger.debug("_workflow_remove(%s)", name)
        return self._workflow_response(self.removeTicket, name)

    def _workflow_sleep(self, name, seconds=sys.maxint):
        """ Sleep all ready tickets for the workflow """
        self.logger.debug("_workflow_sleep(%s,%s)", name, seconds)
        return self._workflow_response(self.sleepTicket, name, seconds=seconds)

    def _workflow_wake(self, name):
        """ Wake all ready tickets for the workflow """
        self.logger.debug("_workflow_wake(%s)", name)
        return self._workflow_response(self.wakeTicket, name)

if __name__ == "__main__":
    #
    # Process command line arguments with a system of tubes
    #
    parser = argparse.ArgumentParser(description="An automaton: http://en.wiki"
                                     "pedia.org/wiki/Karakuri_ningy%C5%8D")
    parser.add_argument("-c", "--config", metavar="FILE",
                        help="specify a configuration file")
    parser.add_argument("-l", "--log", metavar="FILE",
                        help="specify a log file")
    parser.add_argument("--live", action="store_true",
                        help="do what you do irl")
    parser.add_argument("--log-level", metavar="LEVEL",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR",
                                 "CRITICAL"],
                        default="INFO",
                        help="{DEBUG,INFO,WARNING,ERROR,CRITICAL} (default="
                             "INFO)")
    parser.add_argument("--mongo-host", metavar="HOSTNAME",
                        default="localhost",
                        help="specify the MongoDB hostname (default="
                             "localhost)")
    parser.add_argument("--mongo-port", metavar="PORT", default=27017,
                        type=int,
                        help="specify the MongoDB port (default=27017)")
    parser.add_argument("--jira-password", metavar="PASSWORD",
                        help="specify a JIRA password")
    parser.add_argument("--jira-username", metavar="USERNAME",
                        help="specify a JIRA username")
    parser.add_argument("--pid", metavar="FILE", default="/tmp/karakuri.pid",
                        help="specify the PID file")
    parser.add_argument("--rest-port",  metavar="PORT", default=8080, type=int,
                        help="the RESTful interface port (default=8080)")

    args = parser.parse_args()

    # Process config file if one is specified in the CLI options
    if args.config:
        args.config = os.path.abspath(os.path.expandvars(os.path.expanduser(
            args.config)))

        if not os.access(args.config, os.R_OK):
            print("Unable to read from config file")
            sys.exit(1)

        configParser = ConfigParser(add_help=False, fromfile_prefix_chars='@',
                                    parents=[parser])
        args = configParser.parse_args(args=["@%s" % args.config],
                                       namespace=args)

    # I pity the fool that doesn't keep a log file!
    # i.e. Require a log file
    if args.log:
        args.log = os.path.abspath(os.path.expandvars(os.path.expanduser(
            args.log)))

        if not os.access(os.path.dirname(args.log), os.W_OK):
            print("Unable to write to log file")
            sys.exit(3)
    else:
        print("Please specify a log file")
        sys.exit(2)

    # Require a JIRA login for the time being
    if not args.jira_username or not args.jira_password:
        print("Please specify a JIRA username and password")
        sys.exit(4)

    k = karakuri(args)

    # Initialize JIRA++
    jirapp = jirapp(args.jira_username, args.jira_password, k.mongo)
    jirapp.setLive(k.live)

    # Set the Issuer. There can be only one:
    # https://www.youtube.com/watch?v=sqcLjcSloXs
    k.setIssuer(jirapp)

    # Keep it going, keep it going, keep it going full steam
    # Intergalactic Planetary
    k.start()

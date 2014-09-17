#!/usr/bin/env python

import argparse
import bottle
import bson
import bson.json_util
import daemon
import logging
import os
import pidlockfile
import pymongo
import signal
import sys
import threading
import time

from datetime import datetime, timedelta
from jirapp import jirapp
from supportissue import SupportIssue


def getFullPath(path):
    return path and\
        os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


class ConfigParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(ConfigParser, self).__init__(*args, **kwargs)

    def convert_arg_line_to_args(self, line):
        args = line.split()
        for i in range(len(args)):
            if i == 0:
                # ignore commented lines
                if args[i][0] == '#':
                    break
                if not args[i].startswith('--'):
                    # add '--' to simulate cli option
                    args[i] = "--%s" % args[i]
            if not args[i].strip():
                continue

            yield args[i]


class PipeToLogger:
    def __init__(self, logger):
        self.logger = logger

    def write(self, s):
        self.logger.info(s.strip())


class karakuri:
    """ An automaton: http://en.wikipedia.org/wiki/Karakuri_ningy%C5%8D """
    def __init__(self, args):
        """ Wake the beast """
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

        # log what your momma gave ya
        # TODO validate log-level
        logLevel = self.args['log_level']
        # CRITICAL  50
        # ERROR     40
        # WARNING   30
        # INFO      20
        # DEBUG     10
        # NOTSET    0
        # create logger
        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logLevel)
        self.logger.info("Initializing karakuri")

        # output args for later debugging
        self.logger.debug("Parsing args")
        for arg in self.args:
            self.logger.debug("%s %s" % (arg, self.args[arg]))

        # will the real __init__ please stand up, please stand up...
        self.issuer = None
        self.live = True if 'live' in self.args else False

        # initialize databases and collections
        # TODO pass mongodb specific args
        self.mongo = pymongo.MongoClient()
        self.coll_issues = self.mongo.support.issues
        self.coll_workflows = self.mongo.karakuri.workflows
        self.coll_log = self.mongo.karakuri.log
        self.coll_queue = self.mongo.karakuri.queue

    def _buildValidateQuery(self, workflow, iid=None):
        """ Return a MongoDB query that accounts for the workflow prerequisites
        """
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

        if iid is not None:
            # finally, the specified issue must return in the query!
            if not isinstance(iid, bson.ObjectId):
                iid = bson.ObjectId(iid)
            match['_id'] = iid

        return match

    def _performAction(self, action):
        """ Do it like they do on the discovery channel """
        # action must be defined for this issuing system
        if not hasattr(self.issuer, action['name']):
            self.logger.exception("%s is not a supported action",
                                  action['name'])
            return None

        args = list(action['args'])

        # for the sake of logging reduce string arguments
        # to 50 characters and replace \n with \\n
        argString = (', '.join('"' + arg[:50].replace('\n',
                     '\\n') + '"' for arg in args))
        self.logger.info("%s(%s)", action['name'], argString)

        if self.live:
            fun = getattr(self.issuer, action['name'])
            # expand list to function arguments
            res = fun(*args)
        else:
            # simulate success
            res = True

        return res

    def find_and_modify(self, collection, match, updoc):
        """ Wrapper for find_and_modify that handles exceptions """
        res = None

        try:
            res = collection.find_and_modify(match, updoc)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)

        return res

    def find_and_modify_issue(self, match, updoc):
        """ find_and_modify for support.issues that automatically updates the
        'updated' timestamp """
        if "$set" in updoc:
            updoc["$set"]['updated'] = datetime.utcnow()
        else:
            updoc["$set"] = {'updated': datetime.utcnow()}

        return self.find_and_modify(self.coll_issues, match, updoc)

    def find_and_modify_ticket(self, match, updoc):
        """ find_and_modify for karakuri.queue that automatically updates the
        't' timestamp """
        if "$set" in updoc:
            updoc["$set"]['t'] = datetime.utcnow()
        else:
            updoc["$set"] = {'t': datetime.utcnow()}

        return self.find_and_modify(self.coll_queue, match, updoc)

    def find_one(self, collection, match):
        """ Wrapper for find_one that handles exceptions """
        res = None

        try:
            res = collection.find_one(match)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)

        return res

    def log(self, iid, workflowName, action, success):
        """ Log to karakuri.log """
        if not isinstance(iid, bson.ObjectId):
            iid = bson.ObjectId(iid)

        self.logger.debug("log('%s', '%s', '%s', %s)", iid, workflowName,
                          action, success)

        lid = bson.ObjectId()

        log = {'_id': lid, 'iid': iid, 'workflow': workflowName,
               'action': action, 'p': success}

        try:
            self.coll_log.insert(log)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            # TODO write to file on disk instead

        return lid

    def performWorkflow(self, iid, workflowName):
        """ Perform the specified workflow for the given issue """
        if not isinstance(iid, bson.ObjectId):
            iid = bson.ObjectId(iid)

        issue = self.getSupportIssue(iid)
        if not issue:
            self.logger.exception("Unable to getSupportIssue(%s)", iid)
            self.log(iid, workflowName, 'perform', False)
            return None

        workflow = self.getWorkflow(workflowName)
        if not workflow:
            self.logger.exception("Unable to getWorkflow(%s)", workflowName)
            self.log(iid, workflowName, 'perform', False)
            return None

        self.logger.info("performWorkflow('%s', '%s') # %s", iid, workflowName,
                         issue.key)

        # validate that this is still worth running
        # TODO add cleanQueue and removeAll methods
        # TODO add validate to api
        res = self.validate(issue, workflow)
        self.log(iid, workflowName, 'validate', res)

        if not res:
            self.logger.info("Failed to validate workflow requirements, will "
                             "not perform")
            self.log(iid, workflowName, 'perform', False)
            return None

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
            self.log(iid, workflowName, action['name'], res)

            if not res:
                success = False
                break

        lid = self.log(iid, workflowName, 'perform', success)

        if success:
            if self.live:
                match = {'_id': iid}
                updoc = {'$push': {'karakuri.workflows_performed':
                                   {'name': workflowName, 'lid': lid}}}
                issue = self.find_and_modify_issue(match, updoc)

                if not issue:
                    self.logger.exception("Unable to record workflow %s in "
                                          " issue %s # %s", workflowName, iid,
                                          issue.key)
                    self.log(iid, workflowName, 'record', False)
                    # NOTE "To return None, or not to return None?" That is the
                    # question. I believe that I should return None to keep the
                    # ticket from being marked 'done'
                    return None
                else:
                    self.log(iid, workflowName, 'record', True)

        return success

    def processAll(self):
        """ Process all tickets """
        self.logger.info("processAll()")

        match = {'done': False, 'inProg': False, 'approved': True}

        try:
            curs_queue = self.coll_queue.find(match)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return None

        res = True
        count = 0
        for i in curs_queue:
            # if count == self.limit:
            #    self.logger.info("limit met, skipping the rest")
            #    break

            ticket = self.processTicket(i['_id'])
            res &= (ticket and ticket['done'])
            count += 1

        return res

    def processTicket(self, tid):
        """ Process the specified ticket """
        if not isinstance(tid, bson.ObjectId):
            tid = bson.ObjectId(tid)

        self.logger.info("processTicket('%s')", tid)

        match = {'_id': tid, 'done': False, 'inProg': False, 'approved': True}
        updoc = {"$set": {'inProg': True}}
        ticket = self.find_and_modify_ticket(match, updoc)

        if not ticket:
            # most likely the ticket hasn't been approved
            self.logger.exception("Unable to put ticket %s in to progress",
                                  tid)
            return None

        res = self.performWorkflow(ticket['iid'], ticket['workflow'])

        match = {'_id': tid}
        updoc = {"$set": {'done': res, 'inProg': False}}
        ticket = self.find_and_modify_ticket(match, updoc)

        if not ticket:
            self.logger.exception("Unable to take ticket %s out of progress",
                                  tid)
            return None

        return ticket

    def queueAll(self):
        self.logger.info("queueAll()")

        try:
            curs_workflows = self.coll_workflows.find()
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return None

        for workflow in curs_workflows:
            self.logger.info("Considering %s workflow", workflow['name'])
            match = self._buildValidateQuery(workflow)

            # find 'em and get 'er done!
            try:
                curs_issues = self.coll_issues.find(match)
            except pymongo.errors.PyMongoError as e:
                self.logger.exception(e)
                return None

            for i in curs_issues:
                issue = SupportIssue()
                issue.fromDoc(i)

                # we only support JIRA at the moment
                if not issue.hasJIRA():
                    self.logger.info("Skipping unsupported ticketing type!")
                    continue

                # check for karakuri sleepy time
                if not issue.isActive():
                    self.logger.info("Skipping %s as it is not active" %
                                     issue.key)
                    continue

                self.queueTicket(issue.id, workflow['name'])

    def queueTicket(self, iid, workflowName):
        """ Create a ticket for the given issue and workflow """
        if not isinstance(iid, bson.ObjectId):
            iid = bson.ObjectId(iid)

        self.logger.info("queueTicket('%s', '%s')", iid, workflowName)

        # don't queue a ticket that is already queued
        match = {'iid': iid, 'workflow': workflowName, 'done': False}
        if self.coll_queue.find(match).count() != 0:
            self.logger.info("Workflow %s already queued for issue %s",
                             workflowName, iid)
            self.log(iid, workflowName, 'queue', False)
            return None

        now = datetime.utcnow()
        ticket = {'iid': iid, 'workflow': workflowName, 'approved': False,
                  'done': False, 'inProg': False, 't': now, 'start': now}

        try:
            self.coll_queue.insert(ticket)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            self.log(iid, workflowName, 'queue', False)
            return None

        self.log(iid, workflowName, 'queue', True)

        return ticket

    def setIssuer(self, issuer):
        """ Set issue tracking system """
        self.issuer = issuer

    def setLive(self, b):
        """ Lock and load? """
        self.live = b

    def validate(self, iidORissue, workflowNameORworkflow):
        """ Verify the issue satisfies the requirements of the workflow
        """
        # handle the multitude of cases
        if isinstance(iidORissue, SupportIssue):
            iid = iidORissue.id
        elif not isinstance(iidORissue, bson.ObjectId):
            iid = bson.ObjectId(iidORissue)

        if isinstance(workflowNameORworkflow, dict):
            workflow = workflowNameORworkflow
        else:
            workflow = self.getWorkflow(workflowNameORworkflow)

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

    #
    # Methods exposed in the RESTful API
    #

    def getListOfTickets(self, match=None):
        if match is not None:
            curs_queue = self.coll_queue.find(match).\
                sort('start', pymongo.ASCENDING)
        else:
            curs_queue = self.coll_queue.find().\
                sort('start', pymongo.ASCENDING)
        return [q for q in curs_queue]

    def getListOfTicketIds(self, match=None):
        if match is not None:
            curs_queue = self.coll_queue.find(match, {'_id': 1}).\
                sort('start', pymongo.ASCENDING)
        else:
            curs_queue = self.coll_queue.find({'_id': 1}).\
                sort('start', pymongo.ASCENDING)
        return [q['_id'] for q in curs_queue]

    def getListOfWorkflows(self):
        curs_workflows = self.coll_workflows.find()
        return [q for q in curs_workflows]

    def getSupportIssue(self, iid):
        """ Return a SupportIssue for the given iid """
        if not isinstance(iid, bson.ObjectId):
            iid = bson.ObjectId(iid)

        self.logger.debug("getSupportIssue('%s')", iid)

        doc = self.find_one(self.coll_issues, {'_id': iid})

        if doc:
            issue = SupportIssue()
            issue.fromDoc(doc)
            return issue

        self.logger.warning("Issue %s not found!", iid)
        return None

    def getTicket(self, tid):
        """ Return the specified ticket """
        if not isinstance(tid, bson.ObjectId):
            tid = bson.ObjectId(tid)

        self.logger.debug("getTicket('%s')", tid)

        ticket = self.find_one(self.coll_queue, {'_id': tid})

        if ticket:
            return ticket

        self.logger.warning("Ticket %s not found!", tid)
        return None

    def getWorkflow(self, workflowName):
        """ Return the specified workflow """
        self.logger.debug("getWorkflow('%s')", workflowName)

        workflow = self.find_one(self.coll_workflows, {'name': workflowName})

        if workflow:
            return workflow

        self.logger.warning("Workflow %s not found!", workflowName)
        return None

    def listQueue(self):
        print "\tTICKET ID\t\t\tISSUE KEY\tWORKFLOW\tAPPROVED?\tIN PROGRESS?\t"\
              "DONE?\tSTART\t\t\t\tCREATED"
        i = 0
        for ticket in k.getListOfTickets():
            # do not show removed tickets, i.e. tickets with start time within
            # one second of the end of time
            # diff = (datetime.max-ticket['start']).total_seconds()
            # if diff < 1:
            #    continue

            i += 1
            issue = self.getSupportIssue(ticket['iid'])
            print "%5i\t%s\t%s\t%s\t%s\t\t%s\t\t%s\t%s\t%s" %\
                  (i, ticket['_id'], issue.key, ticket['workflow'],
                   ticket['approved'], ticket['inProg'], ticket['done'],
                   ticket['start'].isoformat(),
                   ticket['_id'].generation_time.isoformat())

    def forListOfTickets(self, action, tids, **kwargs):
        """ Perform the given action for the specified tickets """
        res = True
        for tid in tids:
            res &= bool(action(tid, **kwargs))
        return res

    def approveTicket(self, tid):
        match = {'_id': bson.ObjectId(tid)}
        updoc = {"$set": {'approved': True}}
        return self.find_and_modify_ticket(match, updoc)

    def disapproveTicket(self, tid):
        match = {'_id': bson.ObjectId(tid)}
        updoc = {"$set": {'approved': False}}
        return self.find_and_modify_ticket(match, updoc)

    def removeTicket(self, tid):
        match = {'_id': bson.ObjectId(tid)}
        updoc = {"$set": {'done': True, 'removed': True}}
        return self.find_and_modify_ticket(match, updoc)

    def sleepTicket(self, tid, seconds):
        seconds = int(seconds)
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            diff = timedelta(seconds=seconds)
            wakeDate = now + diff

        match = {'_id': bson.ObjectId(tid)}
        updoc = {"$set": {'start': wakeDate}}
        return self.find_and_modify_ticket(match, updoc)

    def wakeTicket(self, tid):
        match = {'_id': bson.ObjectId(tid)}
        updoc = {"$set": {'start': datetime.utcnow()}}
        return self.find_and_modify_ticket(match, updoc)

    def sleepIssue(self, iid, seconds):
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            diff = timedelta(seconds=seconds)
            wakeDate = now + diff

        match = {'_id': bson.ObjectId(iid)}
        updoc = {"$set": {'karakuri.sleep': wakeDate}}
        return self.find_and_modify_issue(match, updoc)

    def wakeIssue(self, iid):
        match = {'_id': bson.ObjectId(iid)}
        updoc = {"$unset": {'karakuri.sleep': ""}}
        return self.find_and_modify_issue(match, updoc)

    #
    # Enter the Daemon
    #
    def run(self):
        self.logger.info("Daemonizing karakuri")

        # Initialize JIRA++
        issuer = jirapp(self.args['jira_username'], self.args['jira_password'],
                        self.mongo)
        issuer.setLive(self.live)

        # Set the Issuer. There can be only one:
        # https://www.youtube.com/watch?v=sqcLjcSloXs
        self.setIssuer(issuer)

        if self.args['rest']:
            b = bottle.Bottle()

            # These are the RESTful API endpoints. There are many like it, but
            # these are them
            b.route('/issue', callback=self._issue_list)
            b.route('/issue/<id>', callback=self._issue_get)
            b.route('/issue/<id>/sleep', callback=self._issue_sleep)
            b.route('/issue/<id>/sleep/<seconds:int>',
                    callback=self._issue_sleep)
            b.route('/issue/<id>/wake', callback=self._issue_wake)
            b.route('/queue', callback=self._queue_list)
            b.route('/queue/approve', callback=self._queue_approve)
            b.route('/queue/disapprove', callback=self._queue_disapprove)
            b.route('/queue/process', callback=self._queue_process)
            b.route('/queue/remove', callback=self._queue_remove)
            b.route('/queue/sleep', callback=self._queue_sleep)
            b.route('/queue/sleep/<seconds:int>', callback=self._queue_sleep)
            b.route('/queue/wake', callback=self._queue_wake)
            b.route('/ticket/<id>', callback=self._ticket_get)
            b.route('/ticket/<id>/approve', callback=self._ticket_approve)
            b.route('/ticket/<id>/disapprove',
                    callback=self._ticket_disapprove)
            b.route('/ticket/<id>/process', callback=self._ticket_process)
            b.route('/ticket/<id>/remove', callback=self._ticket_remove)
            b.route('/ticket/<id>/sleep', callback=self._ticket_sleep)
            b.route('/ticket/<id>/sleep/<seconds:int>',
                    callback=self._ticket_sleep)
            b.route('/ticket/<id>/wake', callback=self._ticket_wake)
            b.route('/workflow', callback=self._workflow_list)
            b.route('/workflow/<name>', callback=self._workflow_get)
            b.route('/workflow/<name>/approve',
                    callback=self._workflow_approve)
            b.route('/workflow/<name>/disapprove',
                    callback=self._workflow_disapprove)
            b.route('/workflow/<name>/process',
                    callback=self._workflow_process)
            b.route('/workflow/<name>/remove', callback=self._workflow_remove)
            b.route('/workflow/<name>/sleep', callback=self._workflow_sleep)
            b.route('/workflow/<name>/sleep/<seconds:int>',
                    callback=self._workflow_sleep)
            b.route('/workflow/<name>/wake', callback=self._workflow_wake)

            thread = threading.Thread(target=b.run,
                                      kwargs=dict(host='localhost',
                                                  port=self.args['port']))
            thread.setDaemon(True)
            thread.start()

        while (1):
            self.logger.info("The Loop, the Loop, the Loop is on fire!")
            time.sleep(5)

    def _issue_list(self):
        """ Return no-way, Jose 404 """
        # TODO implement no-way, Jose 404
        ret = {'res': 1, 'data': []}
        return bson.json_util.dumps(ret)

    def _issue_get(self, id):
        """ Return the issue """
        issue = self.getSupportIssue(id)

        if issue is not None:
            res = 0
        else:
            issue = {'doc': {}}
            res = 1

        ret = {'res': res, 'data': issue.doc}
        return bson.json_util.dumps(ret)

    def _issue_sleep(self, id, seconds=sys.maxint):
        """ Sleep the issue. A sleeping issue cannot have tickets queued """
        res = 0 if self.sleepIssue(id, seconds) is not None else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _issue_wake(self, id):
        """ Wake the issue, i.e. unsleep it """
        res = 0 if self.wakeIssue(id) is not None else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _queue_list(self):
        """ Return a list of tickets """
        match = {'removed': {"$exists": False}}
        tickets = self.getListOfTickets(match)

        if tickets is not None:
            res = 0
        else:
            tickets = []
            res = 1

        ret = {'res': res, 'data': tickets}
        return bson.json_util.dumps(ret)

    def _queue_approve(self):
        """ Approve all active tickets, i.e. those that are not done """
        match = {'done': False}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.approveTicket, tickets)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _queue_disapprove(self):
        """ Disapprove all active tickets """
        match = {'done': False}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.disapproveTicket, tickets)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _queue_process(self):
        """ Process all active tickets """
        match = {'done': False, 'approved': True}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.processTicket, tickets)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _queue_remove(self):
        """ Remove all active tickets """
        match = {'done': False}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.removeTicket, tickets)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _queue_sleep(self, seconds=sys.maxint):
        match = {'done': False}
        """ Sleep all active tickets. A sleeping ticket cannot be dequeued """
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.sleepTicket, tickets, seconds=seconds)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _queue_wake(self):
        """ Wake all active tickets """
        match = {'done': False}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.wakeTicket, tickets)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _ticket_get(self, id):
        """ Return the ticket """
        ticket = self.getTicket(id)

        if ticket is not None:
            res = 0
        else:
            ticket = {}
            res = 1
        ret = {'res': res, 'data': ticket}
        return bson.json_util.dumps(ret)

    def _ticket_approve(self, id):
        """ Approve the ticket """
        res = 0 if self.approveTicket(id) is not None else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _ticket_disapprove(self, id):
        """ Disapprove the ticket """
        res = 0 if self.disapproveTicket(id) is not None else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _ticket_process(self, id):
        """ Process the ticket """
        res = 0 if self.processTicket(id) is not None else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _ticket_remove(self, id):
        """ Remove the ticket """
        res = 0 if self.removeTicket(id) is not None else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _ticket_sleep(self, id, seconds=sys.maxint):
        """ Sleep the ticket. A sleeping ticket cannot be dequeued """
        res = 0 if self.sleepTicket(id, seconds) is not None else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _ticket_wake(self, id):
        """ Wake the ticket, i.e. unsleep it """
        res = 0 if self.wakeTicket(id) is not None else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _workflow_list(self):
        """ Return a list of workflows """
        workflows = self.getListOfWorkflows()

        if workflows is not None:
            res = 0
        else:
            workflows = {}
            res = 1

        ret = {'res': res, 'data': workflows}
        return bson.json_util.dumps(ret)

    def _workflow_get(self, name):
        """ Return the workflow """
        workflow = self.getWorkflow(name)

        if workflow is not None:
            res = 0
        else:
            workflow = {}
            res = 1

        ret = {'res': res, 'data': workflow}
        return bson.json_util.dumps(ret)

    def _workflow_approve(self, name):
        """ Approve all active tickets in the workflow """
        match = {'workflow': name, 'done': False}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.approveTicket, tickets)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _workflow_disapprove(self, name):
        """ Disapprove all active tickets in the workflow """
        match = {'workflow': name, 'done': False}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.disapproveTicket, tickets)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _workflow_process(self, name):
        """ Remove all active tickets in the workflow """
        match = {'workflow': name, 'done': False, 'approved': True}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.removeTicket, tickets)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _workflow_remove(self, name):
        """ Remove all active tickets in the workflow """
        match = {'workflow': name, 'done': False}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.removeTicket, tickets)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _workflow_sleep(self, name, seconds=sys.maxint):
        """ Sleep all active tickets in the workflow """
        match = {'workflow': name, 'done': False}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.sleepTicket, tickets, seconds=seconds)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

    def _workflow_wake(self, name):
        """ Wake all active tickets in the workflow """
        match = {'workflow': name, 'done': False}
        tickets = self.getListOfTicketIds(match)
        res = self.forListOfTickets(self.wakeTicket, tickets)
        res = 0 if res else 1
        ret = {'res': res}
        return bson.json_util.dumps(ret)

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
    parser.add_argument("--log-level", metavar="LEVEL",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR",
                                 "CRITICAL"],
                        default="DEBUG",
                        help="DEBUG/INFO/WARNING/ERROR/CRITICAL")
    parser.add_argument("-p", "--jira-password", metavar="PASSWORD",
                        help="specify a JIRA password")
    parser.add_argument("-u", "--jira-username", metavar="USERNAME",
                        help="specify a JIRA username")
    # support --pid in config files
    parser.add_argument("--pid", default="/tmp/karakuri.pid",
                        help=argparse.SUPPRESS)

    # This is used for cli processing, parser is used for --config
    # file processing so as not to require positional arguments
    parsers = argparse.ArgumentParser(add_help=False, parents=[parser])
    subparsers = parsers.add_subparsers(dest="command",
                                        help='{cli,daemon} -h for help')

    # cli sub-command
    parser_cli = subparsers.add_parser('cli', help='run interactively')
    parser_cli.add_argument("-a", "--approve", action="store_true",
                            help="approve ticket")
    parser_cli.add_argument("-d", "--disapprove", action="store_true",
                            help="disapprove ticket")
    parser_cli.add_argument("-f", "--find", action="store_true",
                            help="find and queue tickets")
    parser_cli.add_argument("--ls", action="store_true",
                            help="list tickets in queue")
    parser_cli.add_argument("-l", "--limit", metavar="NUMBER",
                            help="limit process-all to NUMBER tickets")
    parser_cli.add_argument("--live", action="store_true",
                            help="do what you do irl")
    parser_cli.add_argument("-p", "--process", action="store_true",
                            help="process/dequeue ticket")
    parser_cli.add_argument("--process-all", action="store_true",
                            help="process/dequeue all tickets!")
    parser_cli.add_argument("-r", "--remove", action="store_true",
                            help="remove ticket")
    parser_cli.add_argument("-s", "--sleep", metavar="SECONDS",
                            help="sleep ticket for SECONDS seconds")
    parser_cli.add_argument("-t", "--ticket", metavar="TICKET",
                            help="specify ticket TICKET (comma separated)")
    parser_cli.add_argument("-w", "--wake", action="store_true",
                            help="wake ticket")

    # daemon sub-command
    parser_daemon = subparsers.add_parser('daemon',
                                          help='run as a scary daemon')
    parser_daemon.add_argument("action", choices=["start", "stop", "restart"],
                               help="start/stop/restart")
    parser_daemon.add_argument("--rest",  action="store_true",
                               help="enable the RESTful interface")
    parser_daemon.add_argument("--port",  metavar="PORT", default=8080,
                               type=int,
                               help="specify a port for the RESTful interface")
    parser_daemon.add_argument("--pid", metavar="FILE",
                               help="specify a PID file")

    args = parsers.parse_args()

    # Process config file if one is specified in the CLI options
    if args.config:
        args.config = getFullPath(args.config)
        if not os.access(args.config, os.R_OK):
            logging.error("Unable to read config file")
            sys.exit(1)

        configParser = ConfigParser(add_help=False, fromfile_prefix_chars='@',
                                    parents=[parser])
        args = configParser.parse_args(args=["@%s" % args.config],
                                       namespace=args)

    # Configuration error found, aborting
    error = False

    # Who dareth summon the Daemon!? Answer me these questions three...
    if args.command == "daemon":
        pidfile = pidlockfile.PIDLockFile(args.pid)

        if args.action == "start":
            if pidfile.is_locked():
                print("There is already a running process")
                sys.exit(1)

        if args.action == "stop":
            if pidfile.is_locked():
                pid = pidfile.read_pid()
                os.kill(pid, signal.SIGTERM)
                sys.exit(0)
            else:
                print("There is no running process to stop")
                sys.exit(2)

        if args.action == "restart":
            if pidfile.is_locked():
                pid = pidfile.read_pid()
                os.kill(pid, signal.SIGTERM)
            else:
                print("There is no running process to stop")

        # I pity the fool that doesn't keep a log file!
        if args.log is None:
            logging.error("Please specify a log file")
            error = True
        else:
            args.log = getFullPath(args.log)
            if not os.access(os.path.dirname(args.log), os.W_OK):
                logging.error("Unable to write to log file")
                error = True

        if error:
            sys.exit(2)

        # create file handler and set log level
        logger = logging.getLogger("logger")
        fh = logging.FileHandler(args.log)
        fh.setLevel(args.log_level)
        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(module)s - '
                                      '%(levelname)s - %(message)s')
        # add formatter to file handler
        fh.setFormatter(formatter)
        # add file handler to logger
        logger.addHandler(fh)

        context = daemon.DaemonContext(pidfile=pidfile,
                                       stderr=fh.stream, stdout=fh.stream)

        context.files_preserve = [fh.stream]
        # TODO implment signal_map

        print("Starting...")

        with context:
            k = karakuri(args)
            # redirect stderr and stdout
            sys.__stderr__ = PipeToLogger(k.logger)
            sys.__stdout__ = PipeToLogger(k.logger)

            k.run()

        sys.exit(0)

    # Badasses use the command line start your engines
    if not args.ticket:
        # only an error if find, list_queue or process_all not specified as all
        # other actions are ticket-dependent
        if not args.find and not args.ls and not args.process_all:
            logging.error("Please specify a ticket or tickets")
            error = True
    else:
        # Allow only one ticket-dependent action per run
        # TODO allow double actions, e.g. -ap
        numActions = 0
        for action in [args.approve, args.disapprove, args.process,
                       args.remove, args.sleep, args.wake]:
            if action:
                numActions += 1

        if numActions != 1:
            logging.error("Please specify a single action to take")
            error = True

        # TODO validate this
        args.ticket = [t.strip() for t in args.ticket.split(',')]

    # This is the end. My only friend, the end. RIP Jim.
    if error:
        sys.exit(3)

    k = karakuri(args)

    # If find, do the work, list the queue and exit. The only action I can
    # imagine allowing aside from this is process_all but that scares me
    if args.find:
        k.queueAll()
        k.listQueue()
        sys.exit(0)

    # Ignore other args if list requested
    if args.ls:
        k.listQueue()
        sys.exit(0)

    if args.approve:
        k.forListOfTickets(k.approveTicket, args.ticket)
        sys.exit(0)

    if args.disapprove:
        k.forListOfTickets(k.disapproveTicket, args.ticket)
        sys.exit(0)

    if args.remove:
        k.forListOfTickets(k.removeTicket, args.ticket)
        sys.exit(0)

    if args.sleep:
        k.forListOfTickets(k.sleepTicket, args.ticket,
                           seconds=args.sleep)
        sys.exit(0)

    if args.wake:
        k.forListOfTickets(k.wakeTicket, args.ticket)
        sys.exit(0)

    #
    # Everything from here on down requires an Issuer
    #

    if not args.jira_username or not args.jira_password:
        logging.error("Please specify a JIRA username and password")
        sys.exit(2)

    # Initialize JIRA++
    jirapp = jirapp(args.jira_username, args.jira_password, k.mongo)
    jirapp.setLive(k.live)

    # Set the Issuer. There can be only one:
    # https://www.youtube.com/watch?v=sqcLjcSloXs
    k.setIssuer(jirapp)

    if args.process:
        k.forListOfTickets(k.processTicket, args.ticket)

    if args.process_all:
        k.processAll()

    sys.exit(0)

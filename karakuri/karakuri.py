#!/usr/bin/env python

import bson
import bson.json_util
import logging
import os
import pymongo
import sys

from datetime import datetime, timedelta
from jirapp import jirapp
from optparse import OptionParser
from supportissue import SupportIssue
from ConfigParser import RawConfigParser


class karakuri:
    """ An automaton: http://en.wikipedia.org/wiki/Karakuri_ningy%C5%8D """
    def __init__(self, config):
        """ Wake the beast """
        # TODO parsing of config should be done here
        self.config = config

        # basic logging
        # TODO add verbosity options
        logging.basicConfig(filename=config.get("CLI", "log"),
                            format='[%(asctime)s] %(message)s',
                            level=logging.DEBUG)
        logging.info("Initializing karakuri")

        # output config for later debugging
        logging.debug("Parsing config")
        for s in config.sections():
            logging.debug("[%s]", s)
            logging.debug(config.items(s))

        self.issuer = None
        self.live = False
        self.verbose = False

        # initialize databases and collections
        # TODO load and pass mongodb specific config
        self.mongo = pymongo.MongoClient()
        self.coll_issues = self.mongo.support.issues
        self.coll_workflows = self.mongo.karakuri.workflows
        self.coll_log = self.mongo.karakuri.log
        self.coll_queue = self.mongo.karakuri.queue

    def __buildValidateQuery(self, workflow, iid=None):
        """ Return a MongoDB query that accounts for the workflow prerequisites
        """
        query_string = workflow['query_string']
        match = bson.json_util.loads(query_string)

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

    def find_and_modify(self, collection, match, updoc):
        """ Wrapper for find_and_modify that handles exceptions """
        res = None

        try:
            res = collection.find_and_modify(match, updoc)
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)

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
            logging.exception(e)

        return res

    def log(self, iid, workflowName, action, success):
        """ Log to karakuri.log """
        if not isinstance(iid, bson.ObjectId):
            iid = bson.ObjectId(iid)

        if self.verbose:
            logging.info("log('%s', '%s', '%s', %s)", iid, workflowName,
                         action, success)

        lid = bson.ObjectId()

        log = {'_id': lid, 'iid': iid, 'workflow': workflowName,
               'action': action, 'p': success}

        try:
            self.coll_log.insert(log)
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)
            # TODO write to file on disk instead

        return lid

    def __performAction(self, action):
        """ Do it like they do on the discovery channel """
        # action must be defined for this issuing system
        if not hasattr(self.issuer, action['name']):
            logging.exception("%s is not a supported action", action['name'])
            return None

        args = list(action['args'])

        # for the sake of logging reduce string arguments
        # to 50 characters and replace \n with \\n
        argString = (', '.join('"' + arg[:50].replace('\n',
                     '\\n') + '"' for arg in args))
        logging.info("%s(%s)", action['name'], argString)

        if self.live:
            fun = getattr(self.issuer, action['name'])
            # expand list to function arguments
            res = fun(*args)
        else:
            # simulate success
            res = True

        return res

    def performWorkflow(self, iid, workflowName):
        """ Perform the specified workflow for the given issue """
        if not isinstance(iid, bson.ObjectId):
            iid = bson.ObjectId(iid)

        issue = self.getSupportIssue(iid)
        if not issue:
            logging.exception("Unable to getSupportIssue(%s)", iid)
            self.log(iid, workflowName, 'perform', False)
            return None

        workflow = self.getWorkflow(workflowName)
        if not workflow:
            logging.exception("Unable to getWorkflow(%s)", workflowName)
            self.log(iid, workflowName, 'perform', False)
            return None

        logging.info("performWorkflow('%s', '%s') # %s", iid, workflowName,
                     issue.key)

        # validate that this is still worth running
        # TODO add cleanQueue and removeAll methods
        # TODO add validate to api
        res = self.validate(issue, workflow)
        self.log(iid, workflowName, 'validate', res)

        if not res:
            logging.info("Failed to validate workflow requirements, will "
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

            res = self.__performAction(action)
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
                    logging.exception("Unable to record workflow %s in issue "
                                      "%s # %s", workflowName, iid, issue.key)
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
        logging.info("processAll()")

        match = {'done': False, 'inProg': False, 'approved': True}

        try:
            curs_queue = self.coll_queue.find(match)
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)
            return None

        res = True
        for i in curs_queue:
            ticket = self.processTicket(i['_id'])
            res &= (ticket and ticket['done'])

        return res

    def processTicket(self, tid):
        """ Process the specified ticket """
        if not isinstance(tid, bson.ObjectId):
            tid = bson.ObjectId(tid)

        logging.info("processTicket('%s')", tid)

        match = {'_id': tid, 'done': False, 'inProg': False, 'approved': True}
        updoc = {"$set": {'inProg': True}}
        ticket = self.find_and_modify_ticket(match, updoc)

        if not ticket:
            # most likely the ticket hasn't been approved
            logging.exception("Unable to put ticket %s in to progress", tid)
            return None

        res = self.performWorkflow(ticket['iid'], ticket['workflow'])

        match = {'_id': tid}
        updoc = {"$set": {'done': res, 'inProg': False}}
        ticket = self.find_and_modify_ticket(match, updoc)

        if not ticket:
            logging.exception("Unable to take ticket %s out of progress", tid)
            return None

        return ticket

    def queueAll(self):
        logging.info("queueAll()")

        try:
            curs_workflows = self.coll_workflows.find()
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)
            return None

        for workflow in curs_workflows:
            logging.info("Considering %s workflow", workflow['name'])
            match = self.__buildValidateQuery(workflow)

            # find 'em and get 'er done!
            try:
                curs_issues = self.coll_issues.find(match)
            except pymongo.errors.PyMongoError as e:
                logging.exception(e)
                return None

            for i in curs_issues:
                issue = SupportIssue()
                issue.fromDoc(i)

                # we only support JIRA at the moment
                if not issue.hasJIRA():
                    logging.info("Skipping unsupported ticketing type!")
                    continue

                # check for karakuri sleepy time
                if not issue.isActive():
                    logging.info("Skipping %s as it is not active" % issue.key)
                    continue

                self.queueTicket(issue.id, workflow['name'])

    def queueTicket(self, iid, workflowName):
        """ Create a ticket for the given issue and workflow """
        if not isinstance(iid, bson.ObjectId):
            iid = bson.ObjectId(iid)

        logging.info("queueTicket('%s', '%s')", iid, workflowName)

        # don't queue a ticket that is already queued
        match = {'iid': iid, 'workflow': workflowName, 'done': False}
        if self.coll_queue.find(match).count() != 0:
            logging.info("Workflow %s already queued for issue %s",
                         workflowName, iid)
            self.log(iid, workflowName, 'queue', False)
            return None

        now = datetime.utcnow()
        ticket = {'iid': iid, 'workflow': workflowName, 'approved': False,
                  'done': False, 'inProg': False, 't': now, 'start': now}

        try:
            self.coll_queue.insert(ticket)
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)
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

    def setVerbose(self, b):
        """ Be loquacious? """
        self.verbose = b

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

        logging.info("validate('%s', '%s')", iid, workflow['name'])

        match = self.__buildValidateQuery(workflow, iid)

        if self.verbose:
            logging.debug("%s validate query:", workflow['name'])
            logging.debug(match)

        if self.coll_issues.find(match).count() != 0:
            logging.info("Workflow validated!")
            return True
        else:
            logging.info("Workflow failed validation")
            return False

    #
    # Methods exposed in the RESTful API
    #

    def getListOfTickets(self, match=None):
        if match is not None:
            curs_queue = self.coll_queue.find(match).sort('start', pymongo.ASCENDING)
        else:
            curs_queue = self.coll_queue.find().sort('start', pymongo.ASCENDING)
        return [q for q in curs_queue]

    def getListOfTicketIds(self, match=None):
        if match is not None:
            curs_queue = self.coll_queue.find(match, {'_id': 1}).sort('start', pymongo.ASCENDING)
        else:
            curs_queue = self.coll_queue.find({'_id': 1}).sort('start', pymongo.ASCENDING)
        return [q['_id'] for q in curs_queue]

    def getListOfWorkflows(self):
        curs_workflows = self.coll_workflows.find()
        return [q for q in curs_workflows]

    def getSupportIssue(self, iid):
        """ Return a SupportIssue for the given iid """
        if not isinstance(iid, bson.ObjectId):
            iid = bson.ObjectId(iid)

        if self.verbose:
            logging.info("getSupportIssue('%s')", iid)

        doc = self.find_one(self.coll_issues, {'_id': iid})

        if doc:
            issue = SupportIssue()
            issue.fromDoc(doc)
            return issue

        logging.warning("Issue %s not found!", iid)
        return None

    def getTicket(self, tid):
        """ Return the specified ticket """
        if not isinstance(tid, bson.ObjectId):
            tid = bson.ObjectId(tid)

        if self.verbose:
            logging.info("getTicket('%s')", tid)

        ticket = self.find_one(self.coll_queue, {'_id': tid})

        if ticket:
            return ticket

        logging.warning("Ticket %s not found!", tid)
        return None

    def getWorkflow(self, workflowName):
        """ Return the specified workflow """
        if self.verbose:
            logging.info("getWorkflow('%s')", workflowName)

        workflow = self.find_one(self.coll_workflows, {'name': workflowName})

        if workflow:
            return workflow

        logging.warning("Workflow %s not found!", workflowName)
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
        # set wakeDate to the end of time and mark as done
        # this will effectively remove the ticket from the
        # queue without removing the document
        wakeDate = datetime.max

        match = {'_id': bson.ObjectId(tid)}
        updoc = {"$set": {'start': wakeDate, 'done': True}}
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

if __name__ == "__main__":
    # Process command line parameters with a system of tubes
    parser = OptionParser()
    parser.add_option("-a", "--approve", action="store_true",
                      help="approve ticket")
    parser.add_option("-c", "--config", default="karakuri.cfg", metavar="FILE",
                      help="configuration file FILE")
    parser.add_option("-d", "--disapprove", action="store_true",
                      help="disapprove ticket")
    parser.add_option("-f", "--find", action="store_true",
                      help="find and queue tickets")
    parser.add_option("--log", default="karakuri.log", metavar="FILE",
                      help="log file FILE")
    parser.add_option("-l", "--list-queue",  action="store_true",
                      help="list tickets in queue")
    parser.add_option("--live", action="store_true",
                      help="do what you do irl")
    parser.add_option("-p", "--process", action="store_true",
                      help="process/dequeue ticket")
    parser.add_option("--process-all", action="store_true",
                      help="process/dequeue all tickets!")
    parser.add_option("-r", "--remove", action="store_true",
                      help="remove ticket")
    parser.add_option("-s", "--sleep", metavar="SECONDS",
                      help="sleep ticket for SECONDS seconds")
    parser.add_option("-t", "--ticket", metavar="TICKET",
                      help="specify ticket TICKET (comma separated)")
    parser.add_option("-v", "--verbose", action="store_true",
                      help="be loquacious")
    parser.add_option("-w", "--wake", action="store_true",
                      help="wake ticket")
    (options, args) = parser.parse_args()

    # Configuration error found, aborting
    error = False

    if not options.config:
        print("Please specify a configuration file")
        error = True
    else:
        # TODO expand to full path and verify readability of configuration file
        configFilename = os.getcwd() + "/" + options.config

    if not options.log:
        print("Please specify a log file")
        error = True
    else:
        # TODO expand to full path and verify writability of configuration file
        logFilename = os.getcwd() + "/" + options.log

    if not options.ticket:
        # only an error if find, list_queue or process_all not specified as all
        # other actions are ticket-dependent
        if not options.find and not options.list_queue and\
                not options.process_all:
            print("Please specify a ticket or tickets")
            error = True
    else:
        # Allow only one ticket-dependent action per run
        # TODO allow double actions, e.g. -ap
        numActions = 0
        for action in [options.approve, options.disapprove, options.process,
                       options.remove, options.sleep, options.wake]:
            if action:
                numActions += 1

        if numActions != 1:
            print("Please specify a single action to take")
            error = True

        # TODO validate this
        options.ticket = [t.strip() for t in options.ticket.split(',')]

    # This is the end. My only friend, the end. RIP Jim.
    if error:
        sys.exit(1)

    # Parse configuration file and initialize karakuri
    config = RawConfigParser()
    config.read(configFilename)
    if not config.has_section("CLI"):
        config.add_section("CLI")
    config.set("CLI", "config", configFilename)
    config.set("CLI", "log", logFilename)

    # TODO add cli options into config
    k = karakuri(config)
    k.setLive(options.live)
    k.setVerbose(options.verbose)

    # If find and queue, do the work, list the queue and exit. The only action
    # I can imagine allowing aside from this is perform_all but that scares me
    if options.find:
        k.queueAll()
        k.listQueue()
        sys.exit(0)

    # Ignore other options if list requested
    if options.list_queue:
        k.listQueue()
        sys.exit(0)

    if options.approve:
        k.forListOfTickets(k.approveTicket, options.ticket)
        sys.exit(0)

    if options.disapprove:
        k.forListOfTickets(k.disapproveTicket, options.ticket)
        sys.exit(0)

    if options.remove:
        k.forListOfTickets(k.removeTicket, options.ticket)
        sys.exit(0)

    if options.sleep:
        k.forListOfTickets(k.sleepTicket, options.ticket,
                           seconds=options.sleep)
        sys.exit(0)

    if options.wake:
        k.forListOfTickets(k.wakeTicket, options.ticket)
        sys.exit(0)

    # Everything from here on down requires an Issuer

    # TODO extract JIRA specific config and pass to JIRA++
    # initialize JIRA++
    jirapp = jirapp(config, k.mongo)
    jirapp.setLive(k.live)

    # Set the Issuer. There can be only one:
    # https://www.youtube.com/watch?v=sqcLjcSloXs
    k.setIssuer(jirapp)

    if options.process:
        k.forListOfTickets(k.processTicket, options.ticket)

    if options.process_all:
        k.processAll()

    sys.exit(0)

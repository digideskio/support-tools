import logging
import os
import pymongo
import sys

from bson import ObjectId
from bson.json_util import loads
from datetime import datetime, timedelta
from jirapp import jirapp
from optparse import OptionParser
from supportissue import SupportIssue
from ConfigParser import RawConfigParser


class karakuri:
    """ An automaton: http://en.wikipedia.org/wiki/Karakuri_ningy%C5%8D """
    def __init__(self, config):
        logging.basicConfig(filename='karakuri.log',
                            format='[%(asctime)s] %(message)s',
                            level=logging.DEBUG)
        logging.info("initializing karakuri")

        self.config = config
        self.live = False
        self.issuer = None
        self.verbose = True

        # output config for later debugging
        logging.debug("parsing config file")
        for s in config.sections():
            logging.debug("[%s]", s)
            logging.debug(config.items(s))

        # initialize databases and collections
        # TODO load mongodb specific config
        self.mongo = pymongo.MongoClient()
        self.coll_issues = self.mongo.support.issues
        self.coll_workflows = self.mongo.karakuri.workflows
        self.coll_log = self.mongo.karakuri.log
        self.coll_queue = self.mongo.karakuri.queue

    def find_and_modify(self, collection, match, updoc):
        res = None

        try:
            res = collection.find_and_modify(match, updoc)
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)

        return res

    def find_and_modify_issue(self, match, updoc):
        if "$set" in updoc:
            updoc["$set"]['updated'] = datetime.utcnow()
        else:
            updoc["$set"] = {'updated': datetime.utcnow()}

        return self.find_and_modify(self.coll_issues, match, updoc)

    def find_and_modify_ticket(self, match, updoc):
        if "$set" in updoc:
            updoc["$set"]['t'] = datetime.utcnow()
        else:
            updoc["$set"] = {'t': datetime.utcnow()}

        return self.find_and_modify(self.coll_queue, match, updoc)

    def find_one(self, collection, match):
        res = None

        try:
            res = collection.find_one(match)
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)

        return res

    def log(self, iid, workflowName, action, success):
        logging.info("log('%s', '%s', '%s', %s)", iid, workflowName,
                     action, success)

        lid = ObjectId()

        doc = {'_id': lid, 'iid': iid, 'workflow': workflowName,
               'action': action, 'p': success}

        try:
            self.coll_log.insert(doc)
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)
            # TODO log to files on local disk instead

        return lid

    def performWorkflow(self, iid, workflowName):
        """ Perform the workflow for the given issue """
        logging.info("performWorkflow('%s', '%s')", iid, workflowName)

        # validate that this is still worth running
        if self.validate(iid, workflowName):
            self.log(iid, workflowName, 'validate', True)
        else:
            logging.info("Issue does not satisfy workflow requirements, "
                         "will !perform")
            self.log(iid, workflowName, 'validate', False)
            return None

        issue = self.getSupportIssue(iid)
        if not issue:
            logging.exception("unable to get SupportIssue for %s" % iid)
            return None

        workflow = self.getWorkflow(workflowName)
        if not workflow:
            logging.exception("unable to get workflow for %s" % workflowName)
            return None

        # so far so good
        success = True

        for action in workflow['actions']:
            # ensure action is defined for this ticketing system
            if not hasattr(self.issuer, action['name']):
                logging.exception("%s is not a supported action" %
                                  action['name'])
                return None

            args = []

            if 'args' in action:
                args = list(action['args'])
            else:
                args = []

            # first argument is issuer-dependent
            # JIRA takes a JIRA-key
            args.insert(0, issue.jiraKey)

            # for the sake of logging reduce string arguments
            # to 50 characters and replace \n with \\n
            argString = (', '.join('"' + arg[:50].replace('\n',
                         '\\n') + '"' for arg in args))
            logging.info("Calling %s(%s)" % (action['name'], argString))

            if self.live:
                f = getattr(self.issuer, action['name'])
                # expand list to function arguments
                r = f(*args)
            else:
                # simulate success
                r = True

            if not r:
                success = False
                break

        lid = self.log(issue.id, workflowName, 'perform', success)

        if success:
            match = {'_id': issue.id}
            updoc = {'$push': {'karakuri.workflows_performed':
                               {'name': workflowName, 'lid': lid}}}
            self.find_and_modify_issue(match, updoc)

        return success

    def processTicket(self, tid):
        """ Process the queued ticket """
        logging.info("processTicket('%s')", tid)

        match = {'_id': ObjectId(tid)}
        updoc = {"$set": {'inProg': True}}

        ticket = self.find_and_modify_ticket(match, updoc)

        if not ticket:
            logging.exception("unable to find and modify ticket %s", tid)
            return None

        res = self.performWorkflow(ticket['iid'], ticket['workflow'])
        updoc = {"$set": {'done': res, 'inProg': False}}
        ticket = self.find_and_modify_ticket(match, updoc)

        return ticket

    def processAll(self):
        """ Process all queued tickets """
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

    def queue(self, iid, workflowName):
        logging.info("queue('%s', '%s')", iid, workflowName)

        # don't queue a workflow that is already queued
        match = {'iid': iid, 'workflow': workflowName}
        if self.coll_queue.find(match).count() != 0:
            logging.info("ticket to perform '%s' on '%s' already exists",
                         workflowName, iid)
            self.log(iid, workflowName, 'queue', False)
            # return ticket?
            return None

        now = datetime.utcnow()
        doc = {'iid': iid, 'workflow': workflowName, 'approved': False,
               'done': False, 'inProg': False, 't': now, 'start': now}

        try:
            self.coll_queue.insert(doc)
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)
            return None

        self.log(iid, workflowName, 'queue', True)
        return doc

    def queueAll(self):
        logging.info("queueAll()")

        try:
            curs_workflows = self.coll_workflows.find()
        except pymongo.errors.PyMongoError as e:
            logging.exception(e)
            return None

        for workflow in curs_workflows:
            logging.info("Considering %s workflow" % workflow['name'])

            query_string = workflow['query_string']
            match = loads(query_string)

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
                logging.exception(e)
                return None

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
                    self.queue(issue.id, workflow['name'])

    def setLive(self, b):
        """ Lock and load? """
        self.live = b

    def setIssuer(self, issuer):
        self.issuer = issuer

    def validate(self, iid, workflowName):
        """ Verify that the given issue satisfies the requirements to run the
        specified workflow """
        logging.info("validate('%s', '%s')", iid, workflowName)

        workflow = self.getWorkflow(workflowName)

        if not workflow:
            logging.exception("unable to get workflow for %s" % workflowName)
            return None

        query_string = workflow['query_string']
        match = loads(query_string)

        # has workflow already been processed for this issue?
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
        match['_id'] = iid

        if self.verbose:
            logging.debug(match)

        if self.coll_issues.find(match).count() == 1:
            logging.info("workflow validated")
            return True
        else:
            logging.info("workflow failed validation")
            return False

    #
    # Methods exposed in the RESTful API
    #

    def getListOfTickets(self):
        # it's a capped collection, shouldn't need to sort
        curs_queue = self.coll_queue.find()
        return [q for q in curs_queue]

    def getListOfWorkflows(self):
        curs_workflows = self.coll_workflows.find()
        return [q for q in curs_workflows]

    def getSupportIssue(self, iid):
        """ Return a SupportIssue for the given iid """
        if not isinstance(iid, ObjectId):
            iid = ObjectId(iid)

        if self.verbose:
            logging.info("getSupportIssue('%s')", iid)

        doc = self.find_one(self.coll_issues, {'_id': iid})

        if doc:
            issue = SupportIssue()
            issue.fromDoc(doc)
            return issue

        logging.warning("issue %s !found", iid)
        return None

    def getTicket(self, tid):
        """ Return the specified ticket """
        if not isinstance(tid, ObjectId):
            tid = ObjectId(tid)

        if self.verbose:
            logging.info("getTicket('%s')", tid)

        doc = self.find_one(self.coll_queue, {'_id': tid})

        if doc:
            return doc

        logging.warning("ticket %s !found", tid)
        return None

    def getWorkflow(self, workflowName):
        """ Return the specified workflow """
        if self.verbose:
            logging.info("getWorkflow('%s')", workflowName)

        doc = self.find_one(self.coll_workflows, {'name': workflowName})

        if doc:
            return doc

        logging.warning("workflow document %s !found", workflowName)
        return None

    def listQueue(self):
        print "\tTICKET ID\t\t\tISSUE KEY\tWORKFLOW\tAPPROVED?\tIN PROGRESS?\t"\
              "GOOD TO GO AS OF (START)\tADDED TO QUEUE ON (CREATED)"
        i = 0
        for doc in k.getListOfTickets():
            # do not show removed tickets, i.e. tickets with start time within
            # one second of the end of time
            diff = (datetime.max-doc['start']).total_seconds()
            if diff < 1:
                continue

            i += 1
            issue = self.getSupportIssue(doc['iid'])
            print "%5i\t%s\t%s\t%s\t%s\t\t%s\t\t%s\t%s" %\
                  (i, doc['_id'], issue.key, doc['workflow'],
                   doc['approved'], doc['inProg'], doc['start'].isoformat(),
                   doc['_id'].generation_time.isoformat())

    def forListOfTickets(self, action, tids, **kwargs):
        res = True
        for tid in tids:
            res &= bool(action(tid, **kwargs))
        return res

    def approveTicket(self, tid):
        match = {'_id': ObjectId(tid)}
        updoc = {"$set": {'approved': True}}
        return self.find_and_modify_ticket(match, updoc)

    def disapproveTicket(self, tid):
        match = {'_id': ObjectId(tid)}
        updoc = {"$set": {'approved': False}}
        return self.find_and_modify_ticket(match, updoc)

    def removeTicket(self, tid):
        # documents cannot actually be removed from a capped collection
        # set wakeDate to the end of time
        wakeDate = datetime.max

        match = {'_id': ObjectId(tid)}
        updoc = {"$set": {'start': wakeDate}}
        return self.find_and_modify_ticket(match, updoc)

    def sleepTicket(self, tid, seconds):
        seconds = int(seconds)
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            difference = timedelta(seconds=seconds)
            wakeDate = now + difference

        match = {'_id': ObjectId(tid)}
        updoc = {"$set": {'start': wakeDate}}
        return self.find_and_modify_ticket(match, updoc)

    def wakeTicket(self, tid):
        match = {'_id': ObjectId(tid)}
        updoc = {"$set": {'start': datetime.utcnow()}}
        return self.find_and_modify_ticket(match, updoc)

    def sleepIssue(self, iid, seconds):
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            difference = timedelta(seconds=seconds)
            wakeDate = now + difference

        match = {'_id': ObjectId(iid)}
        updoc = {"$set": {'karakuri.sleep': wakeDate}}
        return self.find_and_modify_issue(match, updoc)

    def wakeIssue(self, iid):
        match = {'_id': ObjectId(iid)}
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
    parser.add_option("-l", "--list-queue", action="store_true",
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
        pass

    if not options.ticket:
        # only an error if find, list_queue or process_all not specified as all
        # other actions are ticket-dependent
        if not options.find and not options.list_queue and\
                not options.process_all:
            print("Please specify a ticket or tickets")
            error = True
    else:
        # Allow only one ticket-dependent action per run
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
    config.read(os.getcwd() + "/" + options.config)
    k = karakuri(config)
    k.setLive(options.live)

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

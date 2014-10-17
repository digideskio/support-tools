#!/usr/bin/env python


import bottle
import bson
import bson.json_util
import karakuricommon
import logging
import pymongo
import re
import string
import sys

from datetime import datetime, timedelta
from jirapp import jirapp
from supportissue import SupportIssue


class karakuri(karakuricommon.karakuribase):
    """ An automaton: http://en.wikipedia.org/wiki/Karakuri_ningy%C5%8D """
    def __init__(self, *args, **kwargs):
        karakuricommon.karakuribase.__init__(self, *args, **kwargs)

        self.issuer = None

        # By default limit is infinite
        if self.args['limit'] is None:
            self.limit = sys.maxint
        else:
            self.limit = self.args['limit']

        # Initialize dbs and collections
        try:
            self.mongo = pymongo.MongoClient(self.args['mongo_host'],
                                             self.args['mongo_port'])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e

        self.coll_issues = self.mongo.support.issues
        self.coll_companies = self.mongo.support.companies
        self.coll_workflows = self.mongo.karakuri.workflows
        self.coll_log = self.mongo.karakuri.log
        self.coll_queue = self.mongo.karakuri.queue
        # For authentication and auditing
        self.coll_users = self.mongo.karakuri.users

        # Initialize throttle
        self.throttle = {}

    def _amiThrottling(self):
        """ Have we reached the daily processing limit? Returns bool """
        self.logger.debug("_amiThrottling()")
        self.throttleRefresh()
        return self.throttle['daily'] >= self.limit

    def approveTask(self, tid):
        """ Approve the task for processing """
        self.logger.debug("approveTask(%s)", tid)
        updoc = {"$set": {'approved': True}}
        return self.updateTask(tid, updoc)

    def buildValidateQuery(self, workflowNameORworkflow, iid=None):
        """ Return a MongoDB query that accounts for the workflow prerequisites
        """
        self.logger.debug("buildValidateQuery(%s,%s)", workflowNameORworkflow,
                          iid)
        if isinstance(workflowNameORworkflow, dict):
            workflow = workflowNameORworkflow
        else:
            res = self.getWorkflow(workflowNameORworkflow)
            if not res['ok']:
                return res
            workflow = res['payload']

        res = self.validateWorkflow(workflow)
        if not res['ok']:
            return res

        query_string = workflow['query_string']

        res = self.loadJson(query_string)
        if not res['ok']:
            return res
        match = res['payload']

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
                return res
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

        return {'ok': True, 'payload': match}

    def createIssue(self, fields):
        """ Create a new issue """
        self.logger.debug("createIssue(%s)", fields)
        fields = SupportIssue(fields).getJIRAFields()
        return self.issuer.createIssue(fields)

    def createWorkflow(self, fields):
        """ Create a new workflow """
        self.logger.debug("createWorkflow(%s)", fields)
        res = self.validateWorkflow(fields)
        if not res['ok']:
            return res

        # does a workflow with this name already exist?
        res = self.getWorkflow(fields['name'])
        if res['ok']:
            return {'ok': False, 'payload': "workflow '%s' already exists"
                    % fields['name']}

        try:
            self.coll_workflows.insert(fields)
        except pymongo.errors.PyMongoError as e:
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': fields}

    def deleteWorkflow(self, name):
        """ Delete the workflow """
        try:
            self.coll_workflows.remove({'name': name})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': None}

    def disapproveTask(self, tid):
        """ Disapprove the task for processing """
        self.logger.debug("disapproveTask(%s)", tid)
        updoc = {"$set": {'approved': False}}
        return self.updateTask(tid, updoc)

    def find_and_modify(self, collection, match, updoc):
        """ Wrapper for find_and_modify that handles exceptions """
        self.logger.debug("find_and_modify(%s,%s,%s)", collection, match,
                          updoc)
        try:
            # return the 'new' updated document
            doc = collection.find_and_modify(match, updoc, new=True)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': doc}

    def find_and_modify_issue(self, match, updoc):
        """ find_and_modify for support.issues that automatically updates the
        'updated' timestamp """
        self.logger.debug("find_and_modify_issue(%s,%s)", match, updoc)
        if "$set" in updoc:
            updoc["$set"]['updated'] = datetime.utcnow()
        else:
            updoc["$set"] = {'updated': datetime.utcnow()}
        return self.find_and_modify(self.coll_issues, match, updoc)

    def find_and_modify_task(self, match, updoc):
        """ find_and_modify for karakuri.queue that automatically updates the
        't' timestamp """
        self.logger.debug("find_and_modify_task(%s,%s)", match, updoc)
        if "$set" in updoc:
            updoc["$set"]['t'] = datetime.utcnow()
        else:
            updoc["$set"] = {'t': datetime.utcnow()}
        return self.find_and_modify(self.coll_queue, match, updoc)

    def find_and_modify_workflow(self, match, updoc):
        """ find_and_modify for karakuri.workflows that automatically updates
        the 't' timestamp """
        self.logger.debug("find_and_modify_workflow(%s,%s)", match, updoc)
        if "$set" in updoc:
            updoc["$set"]['t'] = datetime.utcnow()
        else:
            updoc["$set"] = {'t': datetime.utcnow()}
        return self.find_and_modify(self.coll_workflows, match, updoc)

    def find_one(self, collection, match):
        """ Wrapper for find_one that handles exceptions """
        self.logger.debug("find_one(%s,%s)", collection, match)
        try:
            doc = collection.find_one(match)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': doc}

    def findTasks(self):
        """ Find and queue new tasks """
        self.logger.debug("findTasks()")

        res = self.getListOfWorkflows()
        if not res['ok']:
            return res
        workflows = res['payload']

        tasks = []
        for workflow in workflows:
            res = self.findWorkflowTasks(workflow)
            if not res['ok']:
                return res

            tasks += res['payload']
        return {'ok': True, 'payload': tasks}

    def findWorkflowIssues(self, workflow):
        """ Return list of issues that satisfy the workflow """
        self.logger.debug("findWorkflowIssues(%s)", workflow)
        res = self.buildValidateQuery(workflow)
        if not res['ok']:
            return res
        match = res['payload']

        # find 'em and get 'er done!
        try:
            curs_issues = self.coll_issues.find(match)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': [issue for issue in curs_issues]}

    def findWorkflowTasks(self, workflowNameORworkflow):
        """ Find issues that satisfy the workflow and queue new tasks """
        self.logger.debug("findWorkflowTasks(%s)", workflowNameORworkflow)
        if isinstance(workflowNameORworkflow, dict):
            workflow = workflowNameORworkflow
        else:
            res = self.getWorkflow(workflowNameORworkflow)
            if not res['ok']:
                return res
            workflow = res['payload']

        res = self.findWorkflowIssues(workflow)
        if not res['ok']:
            return res
        issues = res['payload']

        tasks = []
        for i in issues:
            issue = SupportIssue()
            issue.fromDoc(i)

            # we only support JIRA at the moment
            if not issue.hasJIRA():
                self.logger.warning("Skipping unsupported ticket type!")
                continue

            # check for karakuri sleepy time
            if not issue.isActive():
                self.logger.info("Skipping %s as it is not active" % issue.key)
                continue

            res = self.queueTask(issue.id, issue.key, workflow['name'])
            if not res['ok']:
                return res

            if res['payload'] is not None:
                tasks.append(res['payload'])
        return {'ok': True, 'payload': tasks}

    def forListOfTaskIds(self, action, tids, **kwargs):
        """ Perform the given action for the specified tasks """
        self.logger.debug("forListOfTaskIds(%s,%s)", action.__name__, tids)
        tasks = []
        for tid in tids:
            res = action(tid, **kwargs)
            if not res['ok']:
                return res

            if res['payload'] is not None:
                tasks.append(res['payload'])
        return {'ok': True, 'payload': tasks}

    def getIssue(self, iid):
        """ Return issue for the given iid """
        self.logger.debug("getIssue(%s)", iid)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']

        res = self.find_one(self.coll_issues, {'_id': iid})
        if not res['ok']:
            return res
        doc = res['payload']

        if doc is None:
            message = "issue %s not found" % iid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': doc}

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

    def getListOfReadyTaskIds(self, approvedOnly=False):
        self.logger.debug("getListOfReadyTaskIds(%s)", approvedOnly)
        match = {'active': True, 'done': False, 'inProg': False}
        if approvedOnly:
            match['approved'] = True
        return self.getListOfTaskIds(match)

    def getListOfReadyWorkflowTaskIds(self, name, approvedOnly=False):
        self.logger.debug("getListOfReadyWorkflowTaskIds(%s,%s)", name,
                          approvedOnly)
        match = {'active': True, 'done': False, 'inProg': False,
                 'workflow': name}
        if approvedOnly:
            match['approved'] = True
        return self.getListOfTaskIds(match)

    def getListOfTaskIds(self, match={}):
        self.logger.debug("getListOfTaskIds(%s)", match)
        res = self.getListOfTasks(match, {'_id': 1})
        if not res['ok']:
            return res
        return {'ok': True, 'payload': [t['_id'] for t in res['payload']]}

    def getListOfTasks(self, match={}, proj=None):
        self.logger.debug("getListOfTasks(%s,%s)", match, proj)
        try:
            if proj is not None:
                curs_queue = self.coll_queue.find(match, proj).\
                    sort('start', pymongo.ASCENDING)
            else:
                curs_queue = self.coll_queue.find(match).\
                    sort('start', pymongo.ASCENDING)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': [t for t in curs_queue]}

    def getListOfWorkflows(self):
        self.logger.debug("getListOfWorkflows()")
        try:
            # TODO add sort
            curs_workflows = self.coll_workflows.find()
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': [w for w in curs_workflows]}

    def getSupportIssue(self, iid):
        """ Return a SupportIssue for the given iid """
        self.logger.debug("getSupportIssue(%s)", iid)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']

        res = self.find_one(self.coll_issues, {'_id': iid})
        if not res['ok']:
            return res
        doc = res['payload']

        if doc is None:
            message = "issue '%s' not found" % iid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        issue = SupportIssue()
        issue.fromDoc(doc)
        return {'ok': True, 'payload': issue}

    def getTask(self, tid):
        """ Return the specified task """
        self.logger.debug("getTask(%s)", tid)
        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']

        res = self.find_one(self.coll_queue, {'_id': tid})
        if not res['ok']:
            return res
        task = res['payload']

        if task is None:
            message = "task '%s' not found" % tid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': task}

    def _getTemplateValue(self, var, issue):
        """ Return a value for the given template variable. A finite number of
        such template variables are supported and defined below """
        self.logger.debug("_getTemplateValue(%s,%s)", var, issue)
        if var == "COMPANY":
            return {'ok': True, 'payload': issue.company}
        elif var == "SALES_REP":
            match = {'_id': issue.company}
            res = self.find_one(self.coll_companies, match)
            if not res['ok']:
                return res
            company = res['payload']

            if company is not None and 'sales' in company and\
                    company['sales'] is not None:
                sales = ['[~' + name['jira'] + ']' for name in company[
                    'sales']]
                return {'ok': True, 'payload': string.join(sales, ', ')}
        return {'ok': False, 'payload': None}

    def getWorkflow(self, workflowName):
        """ Return the specified workflow """
        self.logger.debug("getWorkflow(%s)", workflowName)
        res = self.find_one(self.coll_workflows, {'name': workflowName})
        if not res['ok']:
            return res
        workflow = res['payload']

        if workflow is None:
            message = "workflow '%s' not found" % workflowName
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': workflow}

    def loadJson(self, string):
        """ Return a JSON-validated dict for the string """
        try:
            res = bson.json_util.loads(string)
        except Exception as e:
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': res}

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

    def _processAction(self, action, issue):
        """ Do it like they do on the discovery channel """
        self.logger.debug("_processAction(%s)", action['name'])

        # action must be defined for this issuing system
        if not hasattr(self.issuer, action['name']):
            message = "'%s' is not a supported action" % action['name']
            self.logger.exception(message)
            return {'ok': False, 'payload': message}

        args = list(action['args'])

        # Replace template variables with real values. A template variable is
        # identified as capital letters between double square brackets
        pattern = re.compile('\[\[([A-Z_]+)\]\]')
        newargs = []
        for arg in args:
            # Use a set to remove repeats
            matches = set(pattern.findall(arg))
            for match in matches:
                res = self._getTemplateValue(match, issue)
                if not res['ok']:
                    return res
                val = res['payload']
                arg = arg.replace('[[%s]]' % match, val)
            newargs.append(arg)

        # For the sake of logging reduce string arguments
        # to 50 characters and replace \n with \\n
        argString = (', '.join('"' + arg[:50].replace('\n',
                     '\\n') + '"' for arg in newargs))
        self.logger.info("%s(%s)", action['name'], argString)

        if self.live:
            method = getattr(self.issuer, action['name'])
            # expand list to function arguments
            res = method(*newargs)
        else:
            # simulate success
            res = {'ok': True, 'payload': True}

        return res

    def processTask(self, tid, **kwargs):
        """ Process the specified task """
        self.logger.debug("processTask(%s)", tid)
        if self._amiThrottling():
            message = "processing limit reached, skipping %s" % tid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}

        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']

        res = self.getTask(tid)
        if not res['ok']:
            return res
        task = res['payload']

        # validate that this is still worth running
        res = self.validateTask(tid)
        # whether or not validateTask ran
        if not res['ok']:
            return res
        # whether or not the task is validated
        if not res['payload']:
            return {'ok': False, 'payload': 'validation failed'}

        match = {'_id': tid, 'active': True, 'done': False, 'inProg': False,
                 'approved': True}
        updoc = {"$set": {'inProg': True}}
        res = self.find_and_modify_task(match, updoc)
        if not res['ok']:
            return res
        task = res['payload']

        if task is None:
            # most likely the task hasn't been approved
            message = "unable to put task '%s' in to progress" % tid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}

        res = self.processWorkflow(task['iid'], task['workflow'])
        if not res['ok']:
            return res

        match = {'_id': tid}
        updoc = {"$set": {'done': True, 'inProg': False}}
        res = self.find_and_modify_task(match, updoc)
        if not res['ok']:
            return res
        task = res['payload']

        if task is None:
            message = "unable to take task %s out of progress" % tid
            self.logger.exception(message)
            return {'ok': False, 'payload': message}

        return {'ok': True, 'payload': task}

    def processWorkflow(self, iid, workflowName, **kwargs):
        """ Perform the specified workflow for the given issue """
        self.logger.info("processWorkflow(%s,%s)", iid, workflowName)

        res = self.getObjectId(iid)
        if not res['ok']:
            self._log(iid, workflowName, 'process', False)
            return res
        iid = res['payload']

        res = self.getSupportIssue(iid)
        if not res['ok']:
            self._log(iid, workflowName, 'process', False)
            return res
        issue = res['payload']

        res = self.getWorkflow(workflowName)
        if not res['ok']:
            self._log(iid, workflowName, 'process', False)
            return res
        workflow = res['payload']

        if workflow is None:
            message = "unable to get workflow '%s'" % workflowName
            self.logger.exception(message)
            self._log(iid, workflowName, 'process', False)
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

            res = self._processAction(action, issue)
            self._log(iid, workflowName, action['name'], res['ok'])

            if not res['ok']:
                success = False
                break

        lid = self._log(iid, workflowName, 'process', success)

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

    def pruneTask(self, tid):
        """ Remove task if it fails validation """
        self.logger.debug("pruneTask(%s)", tid)
        res = self.validateTask(tid)
        if not res['ok']:
            return res
        if not res['payload']:
            res = self.removeTask(tid)
        else:
            res['payload'] = None
        return res

    def queueTask(self, iid, key, workflowName):
        """ Create a task for the given issue and workflow """
        self.logger.info("queueTask(%s,%s,%s)", iid, key, workflowName)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']

        # don't queue a task that is already queued
        match = {'iid': iid, 'workflow': workflowName, 'active': True,
                 'done': False}
        if self.coll_queue.find(match).count() != 0:
            self.logger.warning("workflow '%s' already queued for issue '%s', "
                                "skipping", workflowName, iid)
            self._log(iid, workflowName, 'queue', False)
            return {'ok': True, 'payload': None}

        now = datetime.utcnow()
        task = {'iid': iid, 'key': key, 'workflow': workflowName,
                'approved': False, 'done': False, 'inProg': False, 't': now,
                'start': now, 'active': True}

        try:
            self.coll_queue.insert(task)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            self._log(iid, workflowName, 'queue', False)
            return {'ok': False, 'payload': e}

        self._log(iid, workflowName, 'queue', True)

        return {'ok': True, 'payload': task}

    def removeTask(self, tid):
        """ Remove the task from the queue """
        self.logger.debug("removeTask(%s)", tid)
        updoc = {"$set": {'active': False}}
        return self.updateTask(tid, updoc)

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

    def sleepTask(self, tid, seconds):
        """ Sleep the task, i.e. assign a wake date """
        self.logger.debug("sleepTask(%s)", tid)
        seconds = int(seconds)
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            diff = timedelta(seconds=seconds)
            wakeDate = now + diff

        updoc = {"$set": {'start': wakeDate}}
        return self.updateTask(tid, updoc)

    def throttleRefresh(self):
        oneDayAgo = datetime.utcnow()+timedelta(days=-1)
        # tickets processed successfully in the last day
        match = {"_id": {"$gt": bson.ObjectId.from_datetime(oneDayAgo)},
                 "action": "process", "p": True}
        try:
            self.throttle['daily'] = self.coll_log.find(match).count()
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e
        self.logger.info("daily throttle set to %i",
                         self.throttle['daily'])

    def updateIssue(self, iid, updoc):
        """ They see me rollin' """
        self.logger.debug("updateIssue(%s,%s)", iid, updoc)

        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']
        match = {'_id': iid}
        return self.find_and_modify_issue(match, updoc)

    def updateTask(self, tid, updoc):
        """ They hatin' """
        self.logger.debug("updateTask(%s,%s)", tid, updoc)

        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']
        match = {'_id': tid}
        return self.find_and_modify_task(match, updoc)

    def updateWorkflow(self, name, updoc):
        """ Update an existing workflow """
        self.logger.debug("updateWorkflow(%s,%s)", name, updoc)
        if 'name' not in updoc:
            updoc['name'] = name

        res = self.validateWorkflow(updoc)
        if not res['ok']:
            return res

        match = {'name': name}
        return self.find_and_modify_workflow(match, updoc)

    def validateTask(self, tid):
        """ Validate the task, i.e. that the issue satisfies the requirements
        of the workflow """
        self.logger.debug("validateTask(%s)", tid)

        res = self.getTask(tid)
        if not res['ok']:
            return res
        task = res['payload']
        iid = task['iid']
        workflowName = task['workflow']

        res = self.getWorkflow(workflowName)
        if not res['ok']:
            return res
        workflow = res['payload']

        res = self.buildValidateQuery(workflow, iid)
        if not res['ok']:
            return res
        match = res['payload']
        self.logger.debug("validate query:")
        self.logger.debug(match)

        try:
            res = self.coll_issues.find(match).count() != 0
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        self._log(iid, workflowName, "validate", res)

        if res:
            self.logger.debug("task validated!")
        else:
            self.logger.debug("task !validated")
        return {'ok': True, 'payload': res}

    def validateWorkflow(self, workflow):
        self.logger.debug("validateWorkflow(%s)", workflow)
        if not isinstance(workflow, dict):
            return {'ok': False, 'payload': 'workflow is not of type dict'}
        if 'name' not in workflow:
            return {'ok': False, 'payload': "workflow missing 'name'"}
        if 'query_string' not in workflow:
            return {'ok': False, 'payload': "workflow missing 'query_string'"}
        if 'time_elapsed' not in workflow:
            return {'ok': False, 'payload': "workflow missing 'time_elapsed'"}
        return {'ok': True, 'payload': workflow}

    def wakeIssue(self, iid):
        """ Wake the issue """
        self.logger.debug("wakeIssue(%s)", iid)
        updoc = {"$unset": {'karakuri.sleep': ""}}
        return self.updateIssue(iid, updoc)

    def wakeTask(self, tid):
        """ Wake the task, i.e. mark it ready to go """
        self.logger.debug("wakeTask(%s)", tid)
        updoc = {"$set": {'start': datetime.utcnow()}}
        return self.updateTask(tid, updoc)

    def start(self):
        """ Start the RESTful interface """
        self.logger.debug("start()")
        self.logger.info("karakuri is at REST")

        b = bottle.Bottle(autojson=False)

        # These are the RESTful API endpoints. There are many like it, but
        # these are them
        #########
        #  GET  #
        #########
        b.route('/issue', 'GET', callback=self._issue_list)
        b.route('/issue/<id>', 'GET', callback=self._issue_get)
        b.route('/issue/<id>/sleep', 'GET', callback=self._issue_sleep)
        b.route('/issue/<id>/sleep/<seconds:int>', 'GET',
                callback=self._issue_sleep)
        b.route('/issue/<id>/wake', 'GET', callback=self._issue_wake)
        b.route('/queue', 'GET', callback=self._queue_list)
        b.route('/queue/approve', 'GET', callback=self._queue_approve)
        b.route('/queue/disapprove', 'GET', callback=self._queue_disapprove)
        b.route('/queue/find', 'GET', callback=self._queue_find)
        b.route('/queue/process', 'GET', callback=self._queue_process)
        b.route('/queue/prune', 'GET', callback=self._queue_prune)
        b.route('/queue/remove', 'GET', callback=self._queue_remove)
        b.route('/queue/sleep', 'GET', callback=self._queue_sleep)
        b.route('/queue/sleep/<seconds:int>', 'GET',
                callback=self._queue_sleep)
        b.route('/queue/wake', 'GET', callback=self._queue_wake)
        # a repete ;)
        b.route('/task', 'GET', callback=self._queue_list)
        b.route('/task/<id>', 'GET', callback=self._task_get)
        b.route('/task/<id>/approve', 'GET', callback=self._task_approve)
        b.route('/task/<id>/disapprove', 'GET', callback=self._task_disapprove)
        b.route('/task/<id>/process', 'GET', callback=self._task_process)
        b.route('/task/<id>/prune', 'GET', callback=self._task_prune)
        b.route('/task/<id>/remove', 'GET', callback=self._task_remove)
        b.route('/task/<id>/sleep', 'GET', callback=self._task_sleep)
        b.route('/task/<id>/sleep/<seconds:int>', 'GET',
                callback=self._task_sleep)
        b.route('/task/<id>/wake', 'GET', callback=self._task_wake)
        b.route('/workflow', 'GET', callback=self._workflow_list)
        b.route('/workflow/<name>', 'GET', callback=self._workflow_get)
        b.route('/workflow/<name>/approve', 'GET',
                callback=self._workflow_approve)
        b.route('/workflow/<name>/disapprove', 'GET',
                callback=self._workflow_disapprove)
        b.route('/workflow/<name>/find', 'GET', callback=self._workflow_find)
        b.route('/workflow/<name>/process', 'GET',
                callback=self._workflow_process)
        b.route('/workflow/<name>/prune', 'GET', callback=self._workflow_prune)
        b.route('/workflow/<name>/remove', 'GET',
                callback=self._workflow_remove)
        b.route('/workflow/<name>/sleep', 'GET', callback=self._workflow_sleep)
        b.route('/workflow/<name>/sleep/<seconds:int>', 'GET',
                callback=self._workflow_sleep)
        b.route('/workflow/<name>/wake', 'GET', callback=self._workflow_wake)

        ##########
        #  POST  #
        ##########
        b.route('/issue', 'POST', callback=self._issue_create)
        # TODO b.route('/issue/<id>', 'POST', callback=self._issue_update)
        b.route('/testworkflow', 'POST', callback=self._workflow_test)
        b.route('/workflow', 'POST', callback=self._workflow_create)
        b.route('/workflow/<name>', 'POST', callback=self._workflow_update)

        ###########
        #  DELETE #
        ###########
        b.route('/workflow/<name>', 'DELETE', callback=self._workflow_delete)

        b.run(host=self.args['rest_host'], port=self.args['rest_port'])

    def _authenticated(func):
        """ A decorator for bottle-route callback functions that require
        authentication """
        def wrapped(self, *args, **kwargs):
            # Determine whether or not I am allowed to execute this action
            header = bottle.request.get_header('Authorization')
            if not header:
                bottle.abort(401)
            keyValuePairs = [kv for kv in [keyValue.split('=') for keyValue in
                                           header.split(',')]]
            auth_dict = {}
            for kv in keyValuePairs:
                if len(kv) == 2:
                    auth_dict = {kv[0]: kv[1]}
            token = auth_dict.get('auth_token', None)

            match = {'token': token,
                     'token_expiry_date': {"$gt": datetime.utcnow()}}
            doc = self.coll_users.find_one(match)
            if not doc:
                bottle.abort(401)
            else:
                return func(self, *args, **kwargs)
        return wrapped

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

    @_authenticated
    def _issue_create(self):
        """ Create a JIRA issue """
        self.logger.debug("_issue_create()")
        body = bottle.request.body.read()

        res = self.loadJson(body)
        if not res['ok']:
            return res
        fields = res['payload']

        res = self.createIssue(fields)
        if res['ok']:
            return self._success({'issue': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _issue_get(self, id):
        """ Return the issue """
        self.logger.debug("_issue_get(%s)", id)
        return self._issue_response(self.getIssue, id)

    @_authenticated
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

    @_authenticated
    def _issue_sleep(self, id, seconds=sys.maxint):
        """ Sleep the issue. A sleeping issue cannot have tasks queued """
        self.logger.debug("_issue_sleep(%s,%s)", id, seconds)
        return self._issue_response(self.sleepIssue, id, seconds=seconds)

    @_authenticated
    def _issue_wake(self, id):
        """ Wake the issue, i.e. unsleep it """
        self.logger.debug("_issue_wake(%s)", id)
        return self._issue_response(self.wakeIssue, id)

    @_authenticated
    def _queue_approve(self):
        """ Approve all ready tasks """
        self.logger.debug("_queue_approve()")
        return self._queue_response(self.approveTask)

    @_authenticated
    def _queue_disapprove(self):
        """ Disapprove all ready tasks """
        self.logger.debug("_queue_disapprove()")
        return self._queue_response(self.disapproveTask)

    @_authenticated
    def _queue_find(self):
        """ Find and queue new tasks """
        self.logger.debug("_queue_find()")
        res = self.findTasks()
        if res['ok']:
            return self._success({'tasks': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _queue_list(self):
        """ Return a list of all active tasks """
        self.logger.debug("_queue_list()")
        match = {'active': True}
        res = self.getListOfTasks(match)
        if res['ok']:
            return self._success({'tasks': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _queue_process(self):
        """ Process all ready tasks """
        self.logger.debug("_queue_process()")
        return self._queue_response(self.processTask, approvedOnly=True)

    @_authenticated
    def _queue_prune(self):
        """ Prune all ready tasks """
        self.logger.debug("_queue_prune()")
        return self._queue_response(self.pruneTask)

    @_authenticated
    def _queue_remove(self):
        """ Remove all ready tasks """
        self.logger.debug("_queue_remove()")
        return self._queue_response(self.removeTask)

    def _queue_response(self, method, **kwargs):
        self.logger.debug("_queue_response(%s)", method.__name__)
        res = self.getListOfReadyTaskIds(**kwargs)
        if res['ok']:
            res = self.forListOfTaskIds(method, res['payload'], **kwargs)
            if res['ok']:
                return self._success({'tasks': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _queue_sleep(self, seconds=sys.maxint):
        """ Sleep all ready tasks """
        self.logger.debug("_queue_sleep(%s)", seconds)
        return self._queue_response(self.sleepTask, seconds=seconds)

    @_authenticated
    def _queue_wake(self):
        """ Wake all ready tasks """
        self.logger.debug("_queue_wake()")
        return self._queue_response(self.wakeTask)

    @_authenticated
    def _task_approve(self, id):
        """ Approve the task """
        self.logger.debug("_task_approve(%s)", id)
        return self._task_response(self.approveTask, id)

    @_authenticated
    def _task_disapprove(self, id):
        """ Disapprove the task """
        self.logger.debug("_task_disapprove(%s)", id)
        return self._task_response(self.disapproveTask, id)

    @_authenticated
    def _task_get(self, id):
        """ Return the task """
        self.logger.debug("_task_get(%s)", id)
        return self._task_response(self.getTask, id)

    @_authenticated
    def _task_process(self, id):
        """ Process the task """
        self.logger.debug("_task_process(%s)", id)
        return self._task_response(self.processTask, id, approvedOnly=True)

    @_authenticated
    def _task_prune(self, id):
        """ Prune the task """
        self.logger.debug("_task_prune(%s)", id)
        return self._task_response(self.pruneTask, id)

    @_authenticated
    def _task_remove(self, id):
        """ Remove the task """
        self.logger.debug("_task_remove(%s)", id)
        return self._task_response(self.removeTask, id)

    def _task_response(self, method, id, **kwargs):
        self.logger.debug("_task_response(%s,%s)", method.__name__, id)
        res = method(id, **kwargs)
        if res['ok']:
            return self._success({'task': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _task_sleep(self, id, seconds=sys.maxint):
        """ Sleep the task. A sleeping task cannot be processed """
        self.logger.debug("_task_sleep(%s,%s)", id, seconds)
        return self._task_response(self.sleepTask, id, seconds=seconds)

    @_authenticated
    def _task_wake(self, id):
        """ Wake the task, i.e. unsleep it """
        self.logger.debug("_task_wake(%s)", id)
        return self._task_response(self.wakeTask, id)

    @_authenticated
    def _workflow_approve(self, name):
        """ Approve all ready tasks for the workflow """
        self.logger.debug("_workflow_approve(%s)", name)
        return self._workflow_response(self.approveTask, name)

    @_authenticated
    def _workflow_create(self):
        """ Create a workflow """
        self.logger.debug("_workflow_create()")
        body = bottle.request.body.read()

        res = self.loadJson(body)
        if not res['ok']:
            return res
        fields = res['payload']

        res = self.createWorkflow(fields)
        if res['ok']:
            return self._success({'workflow': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _workflow_delete(self, name):
        """ Delete the workflow """
        self.logger.debug("_workflow_delete(%s)", name)
        res = self.deleteWorkflow(name)
        if res['ok']:
            return self._success({'workflow': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _workflow_disapprove(self, name):
        """ Disapprove all ready tasks for the workflow """
        self.logger.debug("_workflow_disapprove(%s)", name)
        return self._workflow_response(self.disapproveTask, name)

    @_authenticated
    def _workflow_find(self, name):
        """ Find and queue new tasks for the workflow """
        self.logger.debug("_workflow_find()")
        res = self.findWorkflowTasks(name)
        if res['ok']:
            return self._success({'tasks': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _workflow_get(self, name):
        """ Return the workflow """
        self.logger.debug("_workflow_get(%s)", name)
        res = self.getWorkflow(name)
        if res['ok']:
            return self._success({'workflow': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _workflow_list(self):
        """ Return a list of workflows """
        self.logger.debug("_workflow_list()")
        res = self.getListOfWorkflows()
        if res['ok']:
            return self._success({'workflows': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _workflow_process(self, name):
        """ Process all ready tasks for the workflow """
        self.logger.debug("_workflow_process(%s)", name)
        return self._workflow_response(self.processTask, name,
                                       approvedOnly=True)

    @_authenticated
    def _workflow_prune(self, name):
        """ Prune all ready tasks for the workflow """
        self.logger.debug("_workflow_prune(%s)", name)
        return self._workflow_response(self.pruneTask, name)

    @_authenticated
    def _workflow_remove(self, name):
        """ Remove all ready tasks for the workflow """
        self.logger.debug("_workflow_remove(%s)", name)
        return self._workflow_response(self.removeTask, name)

    def _workflow_response(self, method, name, **kwargs):
        self.logger.debug("_workflow_response(%s,%s)", method.__name__, name)
        res = self.getListOfReadyWorkflowTaskIds(name, **kwargs)
        if res['ok']:
            res = self.forListOfTaskIds(method, res['payload'], **kwargs)
            if res['ok']:
                return self._success({'tasks': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _workflow_sleep(self, name, seconds=sys.maxint):
        """ Sleep all ready tasks for the workflow """
        self.logger.debug("_workflow_sleep(%s,%s)", name, seconds)
        return self._workflow_response(self.sleepTask, name, seconds=seconds)

    @_authenticated
    def _workflow_test(self):
        """ Return a list of tickets that satisfy the workflow requirements """
        self.logger.debug("_workflow_test()")
        body = bottle.request.body.read()

        res = self.loadJson(body)
        if not res['ok']:
            return res
        fields = res['payload']

        res = self.validateWorkflow(fields)
        if not res['ok']:
            return self._error(res['payload'])

        res = self.findWorkflowIssues(fields)
        if res['ok']:
            return self._success({'issues': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _workflow_update(self, name):
        """ Update a workflow """
        self.logger.debug("_workflow_update()")
        body = bottle.request.body.read()

        res = self.loadJson(body)
        if not res['ok']:
            return res
        fields = res['payload']

        res = self.updateWorkflow(name, fields)
        if res['ok']:
            return self._success({'workflow': res['payload']})
        return self._error(res['payload'])

    @_authenticated
    def _workflow_wake(self, name):
        """ Wake all ready tasks for the workflow """
        self.logger.debug("_workflow_wake(%s)", name)
        return self._workflow_response(self.wakeTask, name)

if __name__ == "__main__":
    parser = karakuricommon.karakuriparser(description="An automaton: http://e"
                                                       "n.wikipedia.org/wiki/K"
                                                       "arakuri_ningy%C5%8D")
    parser.add_config_argument("--limit", metavar="NUMBER", type=int,
                               help="limit process'ing to NUMBER tasks")
    parser.add_config_argument("--mongo-host", metavar="HOSTNAME",
                               default="localhost",
                               help="specify the MongoDB hostname (default="
                                    "localhost)")
    parser.add_config_argument("--mongo-port", metavar="PORT", default=27017,
                               type=int,
                               help="specify the MongoDB port (default=27017)")
    parser.add_config_argument("--jira-password", metavar="PASSWORD",
                               help="specify a JIRA password")
    parser.add_config_argument("--jira-username", metavar="USERNAME",
                               help="specify a JIRA username")
    parser.add_config_argument("--rest-host",  metavar="HOSTNAME",
                               default="localhost",
                               help="the RESTful interface hostname "
                               "(default=localhost)")
    parser.add_config_argument("--rest-port",  metavar="PORT", default=8080,
                               type=int,
                               help="the RESTful interface port "
                                    "(default=8080)")

    args = parser.parse_args()

    # I pity the fool that doesn't keep a log file!
    if args.log is None:
        print("Please specify a log file")
        sys.exit(1)

    logger = logging.getLogger("logger")
    fh = logging.FileHandler(args.log)
    fh.setLevel(args.log_level)
    formatter = logging.Formatter('%(asctime)s - %(module)s - '
                                  '%(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Require a JIRA login for the time being
    if not args.jira_username or not args.jira_password:
        print("Please specify a JIRA username and password")
        sys.exit(2)

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

    sys.exit(0)

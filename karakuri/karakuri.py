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

        # This could represent JIRA, Salesforce, what have you...
        self.issuer = None

        # By default limits are infinite
        if self.args['global_limit'] is None:
            self.global_limit = sys.maxint
        else:
            self.global_limit = self.args['global_limit']

        if self.args['user_limit'] is None:
            self.user_limit = sys.maxint
        else:
            self.user_limit = self.args['user_limit']

        if self.args['company_limit'] is None:
            self.company_limit = sys.maxint
        else:
            self.company_limit = self.args['company_limit']

        # Initialize dbs and collections
        try:
            self.mongo = pymongo.MongoClient(self.args['mongo_uri'])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e

        self.coll_issues = self.mongo.support.issues
        self.coll_companies = self.mongo.support.companies
        self.coll_workflows = self.mongo.karakuri.workflows
        self.coll_log = self.mongo.karakuri.log
        self.coll_queue = self.mongo.karakuri.queue
        self.coll_users = self.mongo.karakuri.users

        # Global, user and company throttles
        self.throttle = {}

    def _amiThrottling(self, **kwargs):
        """ Have we reached a processing limit? Return bool """
        self.logger.debug("_amiThrottling()")
        self.throttleRefresh(**kwargs)
        if kwargs['approvedBy'] not in self.throttle['users']:
            self.throttle['users'][kwargs['approvedBy']] = 0
        if kwargs['company'] not in self.throttle['companies']:
            self.throttle['companies'][kwargs['company']] = 0
        return self.throttle['global'] >= self.global_limit or\
            self.throttle['users'][kwargs['approvedBy']] >= self.user_limit or\
            self.throttle['companies'][kwargs['company']] >= self.company_limit

    def approveTask(self, tid, **kwargs):
        """ Approve the task for processing """
        self.logger.debug("approveTask(%s)", tid)
        updoc = {"$set": {'approved': True,
                          'approvedBy': kwargs['userDoc']['user']}}
        res = self.updateTask(tid, updoc, **kwargs)
        self._log(tid, 'approve', res['ok'], **kwargs)
        return res

    def buildValidateQuery(self, workflowNameORworkflow, iid=None, **kwargs):
        """ Return a MongoDB query that accounts for the workflow prerequisites
        """
        self.logger.debug("buildValidateQuery(%s,%s)", workflowNameORworkflow,
                          iid)
        if isinstance(workflowNameORworkflow, dict):
            workflow = workflowNameORworkflow
        else:
            res = self.getWorkflow(workflowNameORworkflow, **kwargs)
            if not res['ok']:
                return res
            workflow = res['payload']

        res = self.validateWorkflow(workflow, **kwargs)
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

    def createIssue(self, fields, **kwargs):
        """ Create a new issue """
        self.logger.debug("createIssue(%s)", fields)
        # TODO implement logic for multiple issuers
        fields = SupportIssue(fields).getJIRAFields()
        # TODO propagate **kwargs to issuer methods
        return self.issuer.createIssue(fields)

    def createWorkflow(self, fields, **kwargs):
        """ Create a new workflow """
        self.logger.debug("createWorkflow(%s)", fields)
        res = self.validateWorkflow(fields, **kwargs)
        if not res['ok']:
            return res

        # does a workflow with this name already exist?
        res = self.getWorkflow(fields['name'], **kwargs)
        if res['ok']:
            return {'ok': False, 'payload': "workflow '%s' already exists"
                    % fields['name']}

        try:
            self.coll_workflows.insert(fields)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': fields}

    def deleteWorkflow(self, name, **kwargs):
        """ Delete the workflow """
        try:
            self.coll_workflows.remove({'name': name})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': None}

    def disapproveTask(self, tid, **kwargs):
        """ Disapprove the task for processing """
        self.logger.debug("disapproveTask(%s)", tid)
        updoc = {"$set": {'approved': False}, "$unset": {'approvedBy': ""}}
        res = self.updateTask(tid, updoc, **kwargs)
        self._log(tid, 'disapprove', res['ok'], **kwargs)
        return res

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

    def find_and_modify_user(self, match, updoc):
        """ find_and_modify for karakuri.users that automatically updates the
        't' timestamp """
        self.logger.debug("find_and_modify_user(%s,%s)", match, updoc)
        if "$set" in updoc:
            updoc["$set"]['t'] = datetime.utcnow()
        else:
            updoc["$set"] = {'t': datetime.utcnow()}
        return self.find_and_modify(self.coll_users, match, updoc)

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

    def findTasks(self, **kwargs):
        """ Find and queue new tasks """
        self.logger.debug("findTasks()")
        res = self.getListOfWorkflows(**kwargs)
        if not res['ok']:
            return res
        workflows = res['payload']

        tasks = []
        for workflow in workflows:
            res = self.findWorkflowTasks(workflow, **kwargs)
            if not res['ok']:
                return res
            tasks += res['payload']
        return {'ok': True, 'payload': tasks}

    def findWorkflowIssues(self, workflow, **kwargs):
        """ Return list of issues that satisfy the workflow """
        self.logger.debug("findWorkflowIssues(%s)", workflow)
        res = self.buildValidateQuery(workflow, **kwargs)
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

    def findWorkflowTasks(self, workflowNameORworkflow, **kwargs):
        """ Find issues that satisfy the workflow and queue new tasks """
        self.logger.debug("findWorkflowTasks(%s)", workflowNameORworkflow)
        if isinstance(workflowNameORworkflow, dict):
            workflow = workflowNameORworkflow
        else:
            res = self.getWorkflow(workflowNameORworkflow, **kwargs)
            if not res['ok']:
                return res
            workflow = res['payload']

        res = self.findWorkflowIssues(workflow, **kwargs)
        if not res['ok']:
            return res
        issues = res['payload']

        tasks = []
        for i in issues:
            issue = SupportIssue()
            issue.fromDoc(i)

            # we only support JIRA at the moment
            # TODO logic for multiple issuers
            if not issue.hasJIRA():
                self.logger.warning("Skipping unsupported ticket type!")
                continue

            # check for karakuri sleepy time
            if not issue.isActive():
                self.logger.info("Skipping %s as it is not active" % issue.key)
                continue

            tid = bson.ObjectId()
            res = self.queueTask(tid, issue.id, issue.key, issue.company,
                                 workflow['name'], **kwargs)
            self._log(tid, "queue", res['ok'], **kwargs)
            if not res['ok']:
                return res
            if res['payload'] is not None:
                tasks.append(res['payload'])
        return {'ok': True, 'payload': tasks}

    def forListOfTaskIds(self, action, tids, **kwargs):
        """ Perform the given action for the specified tasks """
        self.logger.debug("forListOfTaskIds(%s,%s)", action.__name__, tids)
        tasks = []
        messages = []
        for tid in tids:
            res = action(tid, **kwargs)
            if not res['ok']:
                self.logger.warning(res['payload'])
                messages.append(res['payload'])
            else:
                if res['payload'] is not None:
                    tasks.append(res['payload'])
        # TODO return 'ok': False when?
        return {'ok': True, 'payload': tasks, 'messages': messages}

    def getIssue(self, iid, **kwargs):
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
                self.logger.exception(e)
                return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': id}

    def getListOfReadyTaskIds(self, approvedOnly=False, **kwargs):
        self.logger.debug("getListOfReadyTaskIds(%s)", approvedOnly)
        match = {'active': True, 'done': False, 'inProg': False}
        if approvedOnly:
            match['approved'] = True
        return self.getListOfTaskIds(match, **kwargs)

    def getListOfReadyWorkflowTaskIds(self, name, approvedOnly=False,
                                      **kwargs):
        self.logger.debug("getListOfReadyWorkflowTaskIds(%s,%s)", name,
                          approvedOnly)
        match = {'active': True, 'done': False, 'inProg': False,
                 'workflow': name}
        if approvedOnly:
            match['approved'] = True
        return self.getListOfTaskIds(match, **kwargs)

    def getListOfTaskIds(self, match={}, **kwargs):
        self.logger.debug("getListOfTaskIds(%s)", match)
        res = self.getListOfTasks(match, {'_id': 1}, **kwargs)
        if not res['ok']:
            return res
        return {'ok': True, 'payload': [t['_id'] for t in res['payload']]}

    def getListOfTasks(self, match={}, proj=None, **kwargs):
        self.logger.debug("getListOfTasks(%s,%s)", match, proj)
        try:
            if proj is not None:
                curs_queue = self.coll_queue.find(match, proj)
            else:
                curs_queue = self.coll_queue.find(match)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': [t for t in curs_queue]}

    def getListOfWorkflows(self, **kwargs):
        self.logger.debug("getListOfWorkflows()")
        try:
            curs_workflows = self.coll_workflows.find()
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': [w for w in curs_workflows]}

    def getListOfWorkflowTasks(self, name, **kwargs):
        self.logger.debug("getListOfWorkflowTasks(%s)", name)
        match = {'active': True, 'workflow': name}
        return self.getListOfTasks(match, **kwargs)

    def getSupportIssue(self, iid, **kwargs):
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

    def getTask(self, tid, **kwargs):
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

    def _getTemplateValue(self, var, issue, **kwargs):
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

    def getUser(self, _id, **kwargs):
        """ Return the associated user document """
        self.logger.debug("getUser(%s)", _id)
        res = self.find_one(self.coll_users, {'_id': _id})
        if not res['ok']:
            return res
        user = res['payload']

        if user is None:
            message = "user '%s' not found" % _id
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': user}

    def getUserByToken(self, token, **kwargs):
        """ Return the associated user document """
        self.logger.debug("getUserByToken(%s)", token)
        res = self.find_one(self.coll_users, {'token': token})
        if not res['ok']:
            return res
        user = res['payload']

        if user is None:
            message = "user not found for token '%s'" % token
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': user}

    def getWorkflow(self, workflowName, **kwargs):
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
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': res}

    def _log(self, tid, action, success, **kwargs):
        """ Log to karakuri.log <-- that's a collection! """
        self.logger.debug("log(%s,%s,%s)", tid, action, success)
        res = self.getObjectId(tid)
        if not res['ok']:
            return None
        tid = res['payload']

        res = self.getTask(tid)
        if not res['ok']:
            return None
        task = res['payload']

        iid = task['iid']
        workflow = task['workflow']
        company = task['company']

        lid = bson.ObjectId()

        if 'userDoc' in kwargs:
            user = kwargs['userDoc']['user']
        else:
            user = None

        log = {'_id': lid, 'tid': tid, 'iid': iid, 'workflow': workflow,
               'action': action, 'p': success, 'user': user,
               'company': company}

        try:
            self.coll_log.insert(log)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            # TODO write to file on disk instead
        return lid

    def _processAction(self, action, issue, **kwargs):
        """ Do it like they do on the discovery channel """
        self.logger.debug("_processAction(%s,%s)", action['name'], issue)
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
                res = self._getTemplateValue(match, issue, **kwargs)
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
            # TODO extend **kwargs to issuer actions and pass it here
            res = method(*newargs)
        else:
            # simulate success
            res = {'ok': True, 'payload': True}
        return res

    def processTask(self, tid, **kwargs):
        """ Process the specified task """
        self.logger.debug("processTask(%s)", tid)
        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']

        res = self.getTask(tid, **kwargs)
        if not res['ok']:
            return res
        task = res['payload']

        if self._amiThrottling(approvedBy=task['approvedBy'],
                               company=task['company'], **kwargs):
            message = "processing limit reached, skipping %s" % tid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}

        # validate that this is still worth running
        res = self.validateTask(tid, **kwargs)
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

        res = self.processWorkflow(tid, task['iid'], task['workflow'],
                                   **kwargs)
        lid = self._log(tid, 'process', res['ok'], **kwargs)
        if not res['ok']:
            return res

        if self.live:
            match = {'_id': task['iid']}
            updoc = {'$push': {'karakuri.workflows_performed':
                               {'name': task['workflow'], 'lid': lid}}}
            res = self.find_and_modify_issue(match, updoc)
            if not res['ok'] or res['payload'] is None:
                message = "unable to record workflow '%s' in issue '%s'"\
                    % (task['workflow'], task['iid'])
                self.logger.exception(message)
                self._log(tid, 'record', False, **kwargs)
                return {'ok': False, 'payload': message}
            self._log(tid, 'record', True, **kwargs)

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

    def processWorkflow(self, tid, iid, workflowName, **kwargs):
        """ Perform the specified workflow for the given issue """
        self.logger.info("processWorkflow(%s,%s)", iid, workflowName)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']

        res = self.getSupportIssue(iid, **kwargs)
        if not res['ok']:
            return res
        issue = res['payload']

        res = self.getWorkflow(workflowName, **kwargs)
        if not res['ok']:
            return res
        workflow = res['payload']

        if workflow is None:
            message = "unable to get workflow '%s'" % workflowName
            self.logger.exception(message)
            return {'ok': False, 'payload': message}

        if 'actions' in workflow:
            for action in workflow['actions']:
                # first argument is issuer-dependent
                # JIRA takes a key
                if 'args' in action:
                    action['args'].insert(0, issue.key)
                else:
                    action['args'] = [issue.key]

                res = self._processAction(action, issue, **kwargs)
                self._log(tid, action['name'], res['ok'], **kwargs)

                if not res['ok']:
                    return res
        return {'ok': True, 'payload': None}

    def pruneTask(self, tid, **kwargs):
        """ Remove task if it fails validation """
        self.logger.debug("pruneTask(%s)", tid)
        res = self.validateTask(tid, **kwargs)
        if not res['ok']:
            return res
        if not res['payload']:
            res = self.removeTask(tid, **kwargs)
        else:
            res['payload'] = None
        return res

    def queueTask(self, tid, iid, key, company, workflowName, **kwargs):
        """ Create a task for the given issue and workflow """
        self.logger.info("queueTask(%s,%s,%s,%s,%s)", tid, iid, key, company,
                         workflowName)
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
            return {'ok': True, 'payload': None}

        now = datetime.utcnow()

        task = {'_id': tid, 'iid': iid, 'key': key, 'company': company,
                'workflow': workflowName, 'approved': False, 'done': False,
                'inProg': False, 't': now, 'start': now, 'active': True,
                'createdBy': kwargs['userDoc']['user']}

        try:
            self.coll_queue.insert(task)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': task}

    def removeTask(self, tid, **kwargs):
        """ Remove the task from the queue """
        self.logger.debug("removeTask(%s)", tid)
        updoc = {"$set": {'active': False}}
        res = self.updateTask(tid, updoc, **kwargs)
        self._log(tid, 'remove', res['ok'], **kwargs)
        return res

    def setIssuer(self, issuer):
        """ Set issue tracking system """
        self.issuer = issuer

    def sleepIssue(self, iid, seconds, **kwargs):
        """ Sleep the issue """
        self.logger.debug("sleepIssue(%s)", iid)
        seconds = int(seconds)
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            diff = timedelta(seconds=seconds)
            wakeDate = now + diff

        updoc = {"$set": {'karakuri.sleep': wakeDate}}
        return self.updateIssue(iid, updoc, **kwargs)

    def sleepTask(self, tid, seconds, **kwargs):
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
        res = self.updateTask(tid, updoc, **kwargs)
        self._log(tid, 'sleep', res['ok'], **kwargs)
        return res

    def throttleRefresh(self, **kwargs):
        oneDayAgo = datetime.utcnow()+timedelta(days=-1)
        # tasks processed successfully in the last day
        match = {"_id": {"$gt": bson.ObjectId.from_datetime(oneDayAgo)},
                 "action": "process", "p": True}
        proj = {'tid': 1, 'company': 1}

        try:
            curr_docs = self.coll_log.find(match, proj)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        processedTids = []
        # re-init
        self.throttle['companies'] = {}
        for doc in curr_docs:
            processedTids.append(doc['tid'])
            if doc['company'] in self.throttle['companies']:
                self.throttle['companies'][doc['company']] += 1
            else:
                self.throttle['companies'][doc['company']] = 1
        self.throttle['global'] = len(processedTids)
        self.logger.info("global throttle set to %i", self.throttle['global'])
        for company in self.throttle['companies']:
            self.logger.info("throttle for company '%s' set to %i", company,
                             self.throttle['companies'][company])

        # determine which users approved these tasks
        # NOTE it's possible to overcount approvals here
        match = {"$match": {"tid": {"$in": processedTids}, "action": "approve",
                 "p": True}}
        group = {"$group": {"_id": "$user", "count": {"$sum": 1}}}
        project = {"$project": {"user": "$_id", "count": "$count", "_id": 0}}

        try:
            res = self.coll_log.aggregate([match, group, project])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        if res['ok']:
            users = res['result']
            # re-init
            self.throttle['users'] = {}
            for user in users:
                self.throttle['users'][user['user']] = user['count']
                self.logger.info("throttle for user '%s' set to %i",
                                 user['user'], user['count'])

    def updateIssue(self, iid, updoc, **kwargs):
        """ They see me rollin' """
        self.logger.debug("updateIssue(%s,%s)", iid, updoc)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']
        match = {'_id': iid}
        return self.find_and_modify_issue(match, updoc)

    def updateTask(self, tid, updoc, **kwargs):
        """ They hatin' """
        self.logger.debug("updateTask(%s,%s)", tid, updoc)
        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']
        match = {'_id': tid}
        return self.find_and_modify_task(match, updoc)

    def updateUser(self, uid, updoc, **kwargs):
        """ Update an existing user """
        self.logger.debug("updateUser(%s,%s)", uid, updoc)
        res = self.getObjectId(uid)
        if not res['ok']:
            return res
        uid = res['payload']
        match = {'_id': uid}
        return self.find_and_modify_user(match, updoc)

    def updateWorkflow(self, name, fields, **kwargs):
        """ Update an existing workflow """
        self.logger.debug("updateWorkflow(%s,%s)", name, fields)
        if "$set" not in fields:
            updoc = {"$set": fields}
        else:
            updoc = fields

        res = self.getWorkflow(name, **kwargs)
        if not res['ok']:
            return res
        workflow = res['payload']

        for key in updoc["$set"]:
            workflow[key] = updoc["$set"][key]

        # validate the workflow to be
        res = self.validateWorkflow(workflow, **kwargs)
        if not res['ok']:
            return res

        match = {'name': name}
        return self.find_and_modify_workflow(match, updoc)

    def validateTask(self, tid, **kwargs):
        """ Validate the task, i.e. that the issue satisfies the requirements
        of the workflow """
        self.logger.debug("validateTask(%s)", tid)
        res = self.getTask(tid, **kwargs)
        if not res['ok']:
            return res
        task = res['payload']
        iid = task['iid']
        workflowName = task['workflow']

        res = self.getWorkflow(workflowName, **kwargs)
        if not res['ok']:
            return res
        workflow = res['payload']

        res = self.buildValidateQuery(workflow, iid, **kwargs)
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
        self._log(tid, "validate", res, **kwargs)

        if res:
            self.logger.debug("task validated!")
        else:
            self.logger.debug("task !validated")
        return {'ok': True, 'payload': res}

    def validateWorkflow(self, workflow, **kwargs):
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

    def wakeIssue(self, iid, **kwargs):
        """ Wake the issue """
        self.logger.debug("wakeIssue(%s)", iid)
        updoc = {"$unset": {'karakuri.sleep': ""}}
        return self.updateIssue(iid, updoc, **kwargs)

    def wakeTask(self, tid, **kwargs):
        """ Wake the task, i.e. mark it ready to go """
        self.logger.debug("wakeTask(%s)", tid)
        updoc = {"$set": {'start': datetime.utcnow()}}
        res = self.updateTask(tid, updoc, **kwargs)
        self._log(tid, 'sleep', res['ok'], **kwargs)
        return res

    def start(self):
        """ Start the RESTful interface """
        self.logger.debug("start()")
        self.logger.info("karakuri is at REST")

        b = bottle.Bottle(autojson=False)

        def authenticated(func):
            """ A decorator for bottle-route callback functions that require
            authentication """
            def wrapped(*args, **kwargs):
                # Determine whether or not I am allowed to execute this action
                header = bottle.request.get_header('Authorization')
                if not header:
                    bottle.abort(401)
                keyValuePairs = [kv for kv in [keyValue.split('=') for keyValue
                                               in header.split(',')]]
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
                    kwargs['userDoc'] = doc
                    return func(*args, **kwargs)
            return wrapped

        @b.hook('before_request')
        def checkAndSetAccessControlAllowOriginHeader():
            if self.args['access_control_allowed_origins'] is not None:
                allowed_origins = self.args['access_control_allowed_origins']\
                                      .split(',')
                origin = bottle.request.get_header('Origin')
                if origin in allowed_origins:
                    bottle.response.set_header('Access-Control-Allow-Origin',
                                               origin)

        def success(data=None):
            ret = {'status': 'success', 'data': data}
            bottle.response.status = 200
            return bson.json_util.dumps(ret)

        def fail(data=None):
            ret = {'status': 'fail', 'data': data}
            bottle.response.status = 403
            return bson.json_util.dumps(ret)

        def error(message=None):
            ret = {'status': 'error', 'message': str(message)}
            bottle.response.status = 403
            return bson.json_util.dumps(ret)

        # These are the RESTful API endpoints. There are many like it, but
        # these are them

        @b.post('/issue')
        @authenticated
        def issue_create(**kwargs):
            body = bottle.request.body.read()

            res = self.loadJson(body)
            if not res['ok']:
                return res
            fields = res['payload']

            res = self.createIssue(fields, **kwargs)
            if res['ok']:
                return success({'issue': res['payload']})
            return error(res['payload'])

        @b.route('/issue/<id>')
        @authenticated
        def issue_get(id, **kwargs):
            return issue_response(self.getIssue, id, **kwargs)

        @b.route('/issue')
        @authenticated
        def issue_list(**kwargs):
            # TODO implement no-way, Jose 404
            return fail()

        def issue_response(method, id, **kwargs):
            res = method(id, **kwargs)
            if res['ok']:
                return success({'issue': res['payload']})
            return error(res['payload'])

        @b.route('/issue/<id>/sleep')
        @b.route('/issue/<id>/sleep/<seconds:int>')
        @authenticated
        def issue_sleep(id, seconds=sys.maxint, **kwargs):
            """ Sleep the issue. A sleeping issue cannot have tasks queued """
            self.logger.debug("issue_sleep(%s,%s)", id, seconds)
            return issue_response(self.sleepIssue, id, seconds=seconds,
                                  **kwargs)

        @b.route('/issue/<id>/wake')
        @authenticated
        def issue_wake(id, **kwargs):
            """ Wake the issue, i.e. unsleep it """
            self.logger.debug("issue_wake(%s)", id)
            return issue_response(self.wakeIssue, id, **kwargs)

        @b.route('/queue/approve')
        @authenticated
        def queue_approve(**kwargs):
            """ Approve all ready tasks """
            self.logger.debug("queue_approve()")
            return queue_response(self.approveTask, **kwargs)

        @b.route('/queue/disapprove')
        @authenticated
        def queue_disapprove(**kwargs):
            """ Disapprove all ready tasks """
            self.logger.debug("queue_disapprove()")
            return queue_response(self.disapproveTask, **kwargs)

        @b.route('/queue/find')
        @authenticated
        def queue_find(**kwargs):
            """ Find and queue new tasks """
            self.logger.debug("queue_find()")
            res = self.findTasks(**kwargs)
            if res['ok']:
                return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/queue')
        @b.route('/task')
        @authenticated
        def queue_list(**kwargs):
            """ Return a list of all active tasks """
            self.logger.debug("queue_list()")
            match = {'active': True}
            res = self.getListOfTasks(match, **kwargs)
            if res['ok']:
                return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/queue/process')
        @authenticated
        def queue_process(**kwargs):
            """ Process all ready tasks """
            self.logger.debug("queue_process()")
            return queue_response(self.processTask, approvedOnly=True,
                                  **kwargs)

        @b.route('/queue/prune')
        @authenticated
        def queue_prune(**kwargs):
            """ Prune all ready tasks """
            self.logger.debug("queue_prune()")
            return queue_response(self.pruneTask, **kwargs)

        @b.route('/queue/remove')
        @authenticated
        def queue_remove(**kwargs):
            """ Remove all ready tasks """
            self.logger.debug("queue_remove()")
            return queue_response(self.removeTask, **kwargs)

        def queue_response(method, **kwargs):
            self.logger.debug("queue_response(%s)", method.__name__)
            res = self.getListOfReadyTaskIds(**kwargs)
            if res['ok']:
                res = self.forListOfTaskIds(method, res['payload'], **kwargs)
                if res['ok']:
                    # TODO res may contain 'messages' as well from failed tasks
                    return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/queue/sleep')
        @b.route('/queue/sleep/<seconds:int>')
        @authenticated
        def queue_sleep(seconds=sys.maxint, **kwargs):
            """ Sleep all ready tasks """
            self.logger.debug("queue_sleep(%s)", seconds)
            return queue_response(self.sleepTask, seconds=seconds, **kwargs)

        @b.route('/queue/wake')
        @authenticated
        def queue_wake(**kwargs):
            """ Wake all ready tasks """
            self.logger.debug("queue_wake()")
            return queue_response(self.wakeTask, **kwargs)

        @b.route('/task/<id>/approve')
        @authenticated
        def task_approve(id, **kwargs):
            """ Approve the task """
            self.logger.debug("task_approve(%s)", id)
            return task_response(self.approveTask, id, **kwargs)

        @b.route('/task/<id>/disapprove')
        @authenticated
        def task_disapprove(id, **kwargs):
            """ Disapprove the task """
            self.logger.debug("task_disapprove(%s)", id)
            return task_response(self.disapproveTask, id, **kwargs)

        @b.route('/task/<id>')
        @authenticated
        def task_get(id, **kwargs):
            """ Return the task """
            self.logger.debug("task_get(%s)", id)
            return task_response(self.getTask, id, **kwargs)

        @b.route('/task/<id>/process')
        @authenticated
        def task_process(id, **kwargs):
            """ Process the task """
            self.logger.debug("task_process(%s)", id)
            return task_response(self.processTask, id, approvedOnly=True,
                                 **kwargs)

        @b.route('/task/<id>/prune')
        @authenticated
        def task_prune(id, **kwargs):
            """ Prune the task """
            self.logger.debug("task_prune(%s)", id)
            return task_response(self.pruneTask, id, **kwargs)

        @b.route('/task/<id>/remove')
        @authenticated
        def task_remove(id, **kwargs):
            """ Remove the task """
            self.logger.debug("task_remove(%s)", id)
            return task_response(self.removeTask, id, **kwargs)

        def task_response(method, id, **kwargs):
            self.logger.debug("task_response(%s,%s)", method.__name__, id)
            res = method(id, **kwargs)
            if res['ok']:
                return success({'task': res['payload']})
            return error(res['payload'])

        @b.route('/task/<id>/sleep')
        @b.route('/task/<id>/sleep/<seconds:int>')
        @authenticated
        def task_sleep(id, seconds=sys.maxint, **kwargs):
            """ Sleep the task. A sleeping task cannot be processed """
            self.logger.debug("task_sleep(%s,%s)", id, seconds)
            return task_response(self.sleepTask, id, seconds=seconds, **kwargs)

        @b.route('/task/<id>/wake')
        @authenticated
        def task_wake(id, **kwargs):
            """ Wake the task, i.e. unsleep it """
            self.logger.debug("task_wake(%s)", id)
            return task_response(self.wakeTask, id, **kwargs)

        @b.route('/user/<id>')
        @authenticated
        def user_get(id, **kwargs):
            """ Return the user """
            self.logger.debug("user_get(%s)", id)
            return user_response(self.getUser, id, **kwargs)

        @b.post('/user/<uid>/workflow/<workflow>')
        @authenticated
        def user_add_workflow(uid, workflow, **kwargs):
            """ Add user workflow """
            self.logger.debug("user_add_workflow(%s,%s)", uid, workflow)
            uid = bson.json_util.loads(uid)
            updoc = {"$addToSet": {'workflows': workflow}}
            return user_response(self.updateUser, uid, updoc, **kwargs)

        @b.delete('/user/<uid>/workflow/<workflow>')
        @authenticated
        def user_remove_workflow(uid, workflow, **kwargs):
            """ Remove user workflow """
            self.logger.debug("user_remove_workflow(%s,%s)", uid, workflow)
            uid = bson.json_util.loads(uid)
            updoc = {"$pull": {'workflows': workflow}}
            return user_response(self.updateUser, uid, updoc, **kwargs)

        @b.post('/login')
        def user_login(**kwargs):
            """ Find a user with the specified auth_token """
            self.logger.debug("user_login()")
            if 'token' in bottle.request.params:
                token = bottle.request.params['token']
                res = self.getUserByToken(token)
                if not res['ok']:
                    return error(res['payload'])
                user = res['payload']

                if user is not None:
                    return success(res['payload'])
            return error("unable to authenticate token")

        def user_response(method, id, *args, **kwargs):
            self.logger.debug("user_response(%s,%s)", method.__name__, id)
            res = method(id, *args, **kwargs)
            if res['ok']:
                return success({'user': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/approve')
        @authenticated
        def workflow_approve(name, **kwargs):
            """ Approve all ready tasks for the workflow """
            return workflow_response(self.approveTask, name, **kwargs)

        @b.post('/workflow')
        @authenticated
        def workflow_create(**kwargs):
            """ Create a workflow """
            body = bottle.request.body.read()

            res = self.loadJson(body)
            if not res['ok']:
                return res
            fields = res['payload']

            res = self.createWorkflow(fields, **kwargs)
            if res['ok']:
                return success({'workflow': res['payload']})
            return error(res['payload'])

        @b.delete('/workflow/<name>')
        @authenticated
        def workflow_delete(name, **kwargs):
            """ Delete the workflow """
            self.logger.debug("workflow_delete(%s)", name)
            res = self.deleteWorkflow(name, **kwargs)
            if res['ok']:
                return success({'workflow': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/disapprove')
        @authenticated
        def workflow_disapprove(name, **kwargs):
            """ Disapprove all ready tasks for the workflow """
            return workflow_response(self.disapproveTask, name, **kwargs)

        @b.route('/workflow/<name>/find')
        @authenticated
        def workflow_find(name, **kwargs):
            """ Find and queue new tasks for the workflow """
            res = self.findWorkflowTasks(name, **kwargs)
            if res['ok']:
                return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>')
        @authenticated
        def workflow_get(name, **kwargs):
            """ Return the workflow """
            res = self.getWorkflow(name, **kwargs)
            if res['ok']:
                return success({'workflow': res['payload']})
            return error(res['payload'])

        @b.route('/workflow')
        @authenticated
        def workflow_list(**kwargs):
            """ Return a list of workflows """
            self.logger.debug("workflow_list()")
            res = self.getListOfWorkflows(**kwargs)
            if res['ok']:
                return success({'workflows': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/process')
        @authenticated
        def workflow_process(name, **kwargs):
            """ Process all ready tasks for the workflow """
            self.logger.debug("workflow_process(%s)", name)
            return workflow_response(self.processTask, name, approvedOnly=True,
                                     **kwargs)

        @b.route('/workflow/<name>/queue')
        @authenticated
        def workflow_queue(name, **kwargs):
            """ Return tasks queued for the workflow """
            self.logger.debug("workflow_queue(%s)", name)
            res = self.getListOfWorkflowTasks(name, **kwargs)
            if res['ok']:
                return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/prune')
        @authenticated
        def workflow_prune(name, **kwargs):
            """ Prune all ready tasks for the workflow """
            self.logger.debug("workflow_prune(%s)", name)
            return workflow_response(self.pruneTask, name, **kwargs)

        @b.route('/workflow/<name>/remove')
        @authenticated
        def workflow_remove(name, **kwargs):
            """ Remove all ready tasks for the workflow """
            self.logger.debug("workflow_remove(%s)", name)
            return workflow_response(self.removeTask, name, **kwargs)

        def workflow_response(method, name, **kwargs):
            self.logger.debug("workflow_response(%s,%s)", method.__name__,
                              name)
            res = self.getListOfReadyWorkflowTaskIds(name, **kwargs)
            if res['ok']:
                res = self.forListOfTaskIds(method, res['payload'], **kwargs)
                if res['ok']:
                    # TODO res may contain 'messages' as well from failed tasks
                    return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/sleep')
        @b.route('/workflow/<name>/sleep/<seconds:int>')
        @authenticated
        def workflow_sleep(name, seconds=sys.maxint, **kwargs):
            """ Sleep all ready tasks for the workflow """
            self.logger.debug("workflow_sleep(%s,%s)", name, seconds)
            return workflow_response(self.sleepTask, name, seconds=seconds,
                                     **kwargs)

        @b.post('/testworkflow')
        @authenticated
        def workflow_test(**kwargs):
            """ Return a list of tickets that satisfy the workflow reqs """
            body = bottle.request.body.read()

            res = self.loadJson(body)
            if not res['ok']:
                return res
            fields = res['payload']

            res = self.validateWorkflow(fields, **kwargs)
            if not res['ok']:
                return error(res['payload'])

            res = self.findWorkflowIssues(fields, **kwargs)
            if res['ok']:
                return success({'issues': res['payload']})
            return error(res['payload'])

        @b.post('/workflow/<name>')
        @authenticated
        def workflow_update(name, **kwargs):
            """ Update a workflow """
            body = bottle.request.body.read()

            res = self.loadJson(body)
            if not res['ok']:
                return res
            fields = res['payload']

            res = self.updateWorkflow(name, fields, **kwargs)
            if res['ok']:
                return success({'workflow': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/wake')
        @authenticated
        def workflow_wake(name, **kwargs):
            """ Wake all ready tasks for the workflow """
            self.logger.debug("workflow_wake(%s)", name)
            return workflow_response(self.wakeTask, name, **kwargs)

        b.run(host=self.args['rest_host'], port=self.args['rest_port'])

if __name__ == "__main__":
    parser = karakuricommon.karakuriparser(description="An automaton: http://e"
                                                       "n.wikipedia.org/wiki/K"
                                                       "arakuri_ningy%C5%8D")
    parser.add_config_argument("--mongo-uri", metavar="MONGO",
                               default="mongodb://localhost:27017",
                               help="specify the MongoDB connection URI (default="
                                    "mongodb://localhost:27017)")
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
    parser.add_config_argument("--global-limit", metavar="NUMBER", type=int,
                               help="limit global process'ing to NUMBER tasks")
    parser.add_config_argument("--user-limit", metavar="NUMBER", type=int,
                               help="limit process'ing to NUMBER tasks per "
                                    "approving user")
    parser.add_config_argument("--company-limit", metavar="NUMBER", type=int,
                               help="limit process'ing to NUMBER tasks per "
                                    "customer")
    parser.add_config_argument("--access-control-allowed-origins",
                               metavar="HOSTPORT",
                               help="comma separated list of origins allowed "
                                    "access control")

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

    # TODO logic to choose issuer; i suppose a new cli arg will be warranted
    # then too
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

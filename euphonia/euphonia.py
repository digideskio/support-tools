#!/usr/bin/env python

import bottle
import bson.json_util
import bson.son
import daemon
import karakuricommon
import logging
import os
import pidlockfile
import pymongo
import pytz
import re
import signal
import string
import sys
import urlparse

from datetime import datetime
from models import groups, tests

utc = pytz.UTC


class Euphonia(karakuricommon.karakuriclient):
    def __init__(self, *args, **kwargs):
        karakuricommon.karakuriclient.__init__(self, *args, **kwargs)

        # Initialize dbs and collections
        try:
            self.mongo = pymongo.MongoClient(self.args['mongo_uri'])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e

        self.db_euphonia = self.mongo.euphonia
        self.coll_grouptests = self.db_euphonia.tests

    def _getTemplateValue(self, var, groupSummary, testDoc=None):
        """ Return a value for the given template variable. A finite number of
        such template variables are supported and defined below """
        self.logger.debug("_getTemplateValue(%s,%s)", var, groupSummary)
        if var == "MMS_GROUP_NAME":
            if 'name' in groupSummary:
                return {'ok': True, 'payload': groupSummary['name']}
        elif var == "MMS_GROUP_ID":
            if '_id' in groupSummary:
                return {'ok': True, 'payload': groupSummary['_id']}
        elif var == "MMS_GROUP_ANCHOR":
            if 'name' in groupSummary:
                gid = groupSummary['_id']
                url = 'https://mms.mongodb.com/host/list/%s' % gid
                return {'ok': True, 'payload': '<a href="%s">%s</a>' %
                        (url, groupSummary['name'])}
        elif var == "LIST_AFFECTED_HOSTS":
            if 'ids' in testDoc:
                res = ""
                for _id in testDoc['ids']:
                    ping = groupSummary['ids'][_id.__str__()]
                    doc = ping['doc']
                    res += '# [https://mms.mongodb.com/host/detail/%s/%s|%s:%s]>\n' %\
                        (ping['gid'], ping['hid'], doc['host'], doc['port'])
                return {'ok': True, 'payload': res}
        elif var == "N_AFFECTED_HOSTS":
            if 'nids' in testDoc:
                return {'ok': True, 'payload': testDoc['nids']}
        elif var == "REPORTER_NAME":
                return {'ok': True, 'payload': 'Jake'}
        elif var == "SALES_REP":
            company = ['company']
            if company is not None and 'sales' in company and\
                    company['sales'] is not None:
                sales = ['[~' + name['jira'] + ']' for name in company[
                    'sales']]
                return {'ok': True, 'payload': string.join(sales, ', ')}
        return {'ok': False, 'payload': None}

    def renderTemplatedComment(self, comment, group_summary, testDoc):
        # Replace template variables with real values. A template variable is
        # identified as capital letters between double square brackets
        pattern = re.compile('\[\[([A-Z_]+)\]\]')
        matches = set(pattern.findall(comment))
        for match in matches:
            res = self._getTemplateValue(match, group_summary, testDoc)
            if not res['ok']:
                continue
            val = res['payload']
            comment = comment.replace('[[%s]]' % match, str(val))
        return comment

    def start(self):
        g = groups.Groups(self.mongo)
        t = tests.Tests(self.db_euphonia)
        # sf = salesforce_client.Salesforce()

        # TODO clean this up
        testDescriptionCache = {
            "greeting": "Hi",
            "opening": "My name is [[REPORTER_NAME]] and I am a member of "
                       "the Proactive Technical Support team here at "
                       "MongoDB, Inc. Proactive Support is a new "
                       "initiative to identify issues in your MongoDB "
                       "deployment before they become problematic. To "
                       "this end we employ automated MMS data aggregation "
                       "scripts to search for patterns consistent with "
                       "known and potential complications. There are a "
                       "couple of potential issues in your MMS group "
                       "[[[MMS_GROUP_NAME]]|https://mms.mongodb.com/host/"
                       "list/[[MMS_GROUP_ID]]] that we would like to "
                       "address in this ticket. It's possible that we "
                       "will discover more issues during the diagnostic "
                       "process, and we will address those in turn.",
            "closing": "We look forward to working with you to resolve "
                       "this issues described above, and we have created "
                       "individual support tickets to track each issue "
                       "(you should receive notifications shortly). "
                       "Please review any tickets at your earliest "
                       "convenience so we can schedule some time to work "
                       "with you.",
            "signoff": "Thanks, The MongoDB Proactive Services Team"
        }
        # populate testDescriptionCache
        try:
            curr_tests = self.coll_grouptests.find({}, {'_id': 0})
        except pymongo.errors.PyMongoError as e:
            raise e
        if curr_tests is not None:
            for test in curr_tests:
                if test['src'] in testDescriptionCache:
                    testDescriptionCache[test['src']][test['name']] = test
                else:
                    testDescriptionCache[test['src']] = {test['name']: test}

        b = bottle.Bottle(autojson=False)

        bottle.TEMPLATE_PATH.insert(0, '%s/views' % self.args['root_webdir'])

        def response(result, cookies=None, template=None, template_data=None):
            self.logger.debug("response(%s,%s,%s,%s)", result, cookies,
                              template, template_data)
            if result['status'] == "success":
                if cookies is not None:
                    for cookie in cookies:
                        if not isinstance(cookie[1], unicode):
                            try:
                                val = bson.json_util.dumps(cookie[1])
                            except Exception as e:
                                val = e
                        else:
                            val = cookie[1]
                        bottle.response.set_cookie(str(cookie[0]), val)
                bottle.response.status = 200
                if template is not None:
                    data = {'data': result['data']}
                    if template_data is not None:
                        for datum in template_data:
                            data[datum] = template_data[datum]
                    return bottle.template(template, data=data)
            elif result['status'] == "fail":
                bottle.response.status = 500
            elif result['status'] == "error":
                bottle.response.status = 400
            return bson.json_util.dumps(result)

        def tokenize(func):
            """ A decorator for bottle-route callback functions to pass
            auth_token cookies """
            def wrapped(*args, **kwargs):
                kwargs['token'] = bottle.request.get_cookie("kk_token")
                return func(*args, **kwargs)
            return wrapped

        @b.post('/login')
        def login():
            token = bottle.request.params.get('kk_token')
            res = self.postRequest("/login", data={'token': token})
            if res['status'] == 'success':
                user = res['data']
                cookies = [(prop, user[prop]) for prop in user]
            else:
                cookies = None
            return response(res, cookies=cookies)

        # ROOT/SUMMARY PAGE
        @b.route('/')
        def index():
            return bottle.redirect('/tasks')

        # GROUP-RELATED ROUTES
        @b.route('/groups/<page>/<query>')
        @b.route('/groups/page/<page>')
        @b.route('/groups')
        @b.route('/groups/')
        def get_groups(page=1, test=None, query=None):
            match = {'failedTests': {"$exists": 1}}
            if query is not None:
                match['gid'] = query
            if test is not None:
                match['failedTest']['test'] = test

            limit = 25
            if page == '':
                page = 1
            page = int(page)
            skip = (page - 1) * limit

            try:
                res = self.db_euphonia.groups.find(match).\
                    sort('score', pymongo.DESCENDING).limit(limit).skip(skip)
            except pymongo.errors.PyMongoError as e:
                print(e)

            groups = [group for group in res]

            return bottle.template('base_page', renderpage="summary",
                                   groups=groups, page=page,
                                   count=len(groups), issue=test)

        @b.route('/group/<gid>')
        def get_group_summary(gid):
            group_summary = g.getGroupSummary(gid)
            testDescriptionCache['greeting'] = self.renderTemplatedComment(
                testDescriptionCache['greeting'], group_summary, None)
            testDescriptionCache['opening'] = self.renderTemplatedComment(
                testDescriptionCache['opening'], group_summary, None)
            testDescriptionCache['closing'] = self.renderTemplatedComment(
                testDescriptionCache['closing'], group_summary, None)
            testDescriptionCache['signoff'] = self.renderTemplatedComment(
                testDescriptionCache['signoff'], group_summary, None)
            for ft in group_summary['failedTests']:
                # render templated comment for this test
                comment = testDescriptionCache[ft['src']][ft['test']][
                    'comment']
                testDescriptionCache[ft['src']][ft['test']]['comment'] = self.\
                    renderTemplatedComment(comment, group_summary, ft)
            if group_summary is not None:
                return bottle.template(
                    'base_page', renderpage="group",
                    group=group_summary,
                    testDescriptionCache=testDescriptionCache)
            else:
                return bottle.redirect('/groups')

        @b.route('/group/<gid>/ignore/<test>')
        def ignore_test(gid, test):
            g.ignore_test(gid, test)
            return bottle.redirect('/group/%s' % gid)

        @b.route('/group/<gid>/include/<test>')
        def include_test(gid, test):
            g.include_test(gid, test)
            return bottle.redirect('/group/%s' % gid)

        # TEST-RELATED ROUTES
        @b.route('/tests')
        def get_failed_tests_summary():
            return bottle.template('base_page', renderpage="tests")

        @b.route('/test')
        def get_tests():
            tobj = t.get_tests()
            output = {"status": "success", "data": {"tests": tobj}}
            return bson.json_util.dumps(output)

        @b.route('/defined_tests')
        def get_tests2():
            tobj = t.get_defined_tests()
            output = {"status": "success", "data": {"defined_tests": tobj}}
            return bson.json_util.dumps(output)

        @b.route('/test/<test>')
        def get_matching_groups(test):
            if test is not None:
                query = {"failedTests.test": test}
                tobj = g.get_failed_tests_summary(sort=[
                    ("priority", pymongo.DESCENDING),
                    ("GroupName", pymongo.ASCENDING)],
                    skip=0, limit=10, query=query)
                output = {"status": "success", "data": tobj}
                return bson.json_util.dumps(output)
            else:
                output = {"status": "success", "data": {}}
                return bson.json_util.dumps(output)

        @b.post('/test')
        def create_test():
            formcontent = bottle.request.body.read()
            test = bson.json_util.loads(formcontent)['test']
            return bson.json_util.dumps(t.create_test(test))

        @b.post('/test/<test_name>')
        def update_test(test_name):
            formcontent = bottle.request.body.read()
            test = bson.json_util.loads(formcontent)['test']
            test_id = bson.json_util.ObjectId(test['_id'])
            test['_id'] = test_id
            return bson.json_util.dumps(t.update_test(test_name, test))

        @b.delete('/test/<test_name>')
        def delete_test(test_name):
            return bson.json_util.dumps(t.delete_test(test_name))

        # ISSUE ROUTES
        @b.route('/tasks')
        @tokenize
        def issue_summary(**kwargs):
            # list of workflows
            res = self.workflowRequest(**kwargs)
            if res['status'] == "success":
                workflows = res['data']['workflows']
            else:
                workflows = []

            workflowMap = {workflow['name']: workflow for workflow in
                           workflows}
            workflowNames = workflowMap.keys()
            workflowNames.sort()

            user_workflows = []
            cookie_workflowNames = bottle.request.get_cookie('workflows')

            # convert the octal
            if cookie_workflowNames:
                cookie_workflowNames = urlparse.unquote(cookie_workflowNames)
                if cookie_workflowNames and cookie_workflowNames != "[]":
                    try:
                        user_workflows = bson.json_util.\
                            loads(cookie_workflowNames)
                        user_workflows.sort()
                    except Exception as e:
                        self.logger.exception(e)

            content = ''
            for workflow in user_workflows:
                content += get_rendered_workflow(workflow, **kwargs)
            return bottle.template(
                'base_page', renderpage="tasks",
                allWorkflows=workflowNames, content=content)

        @b.route('/task/<task>/process')
        @tokenize
        def process_task(task, **kwargs):
            return response(self.taskRequest(task, "process", **kwargs))

        @b.route('/task/<task>/approve')
        @tokenize
        def approve_task(task, **kwargs):
            self.taskRequest(task, "approve")
            return response(self.taskRequest(task, "approve", **kwargs))

        @b.route('/task/<task>/disapprove')
        @tokenize
        def disapprove_task(task, **kwargs):
            return response(self.taskRequest(task, "disapprove", **kwargs))

        @b.route('/task/<task>/remove')
        @tokenize
        def remove_task(task, **kwargs):
            return response(self.taskRequest(task, "remove", **kwargs))

        @b.route('/task/<task>/sleep')
        @tokenize
        def freeze_task(task, **kwargs):
            return response(self.taskRequest(task, "sleep", **kwargs))

        @b.route('/task/<task>/wake')
        @tokenize
        def wake_task(task, **kwargs):
            return response(self.taskRequest(task, "wake", **kwargs))

        @b.route('/task/<task>/sleep/<seconds>')
        @tokenize
        def sleep_task(task, seconds, **kwargs):
            seconds = int(seconds)
            return response(self.taskRequest(task, "sleep", seconds, **kwargs))

        @b.post('/user/<uid>/workflow/<workflow>')
        @tokenize
        def user_add_workflow(uid, workflow, **kwargs):
            """ Add user workflow """
            res = self.postRequest("/user/%s/workflow/%s" % (uid, workflow),
                                   **kwargs)
            return bson.json_util.dumps(res)

        @b.delete('/user/<uid>/workflow/<workflow>')
        @tokenize
        def user_remove_workflow(uid, workflow, **kwargs):
            """ Remove user workflow """
            res = self.deleteRequest("/user/%s/workflow/%s" % (uid, workflow),
                                     **kwargs)
            return bson.json_util.dumps(res)

        @b.route('/workflows')
        @tokenize
        def edit_workflows(**kwargs):
            return bottle.template('base_page', renderpage="workflows")

        @b.post('/testworkflow')
        @tokenize
        def test_workflow(**kwargs):
            formcontent = bottle.request.body.read()
            if 'workflow' in formcontent:
                workflow = bson.json_util.loads(formcontent)['workflow']
                wfstring = bson.json_util.dumps(workflow)
                print wfstring
                res = self.postRequest("/testworkflow", data=wfstring,
                                       **kwargs)
                if res['status'] == "success":
                    if 'data' in res and 'issues' in res['data']:
                        for issue in res['data']['issues']:
                            del issue['jira']['changelog']
                            del issue['jira']['fields']['comment']
                            del issue['jira']['fields']['attachment']
                            if 'karakuri' in issue and 'sleep' in\
                                    issue['karakuri']:
                                del issue['karakuri']['sleep']
                    return bson.json_util.dumps(res)
                else:
                    return res
            msg = {"status": "error",
                   "message": "workflow missing 'query_string'"}
            return bson.json_util.dumps(msg)

        @b.post('/workflow')
        @tokenize
        def create_workflow(**kwargs):
            formcontent = bottle.request.body.read()
            workflow = bson.json_util.loads(formcontent)['workflow']
            wfstring = bson.json_util.dumps(workflow)
            return self.postRequest("/workflow", data=wfstring, **kwargs)

        @b.post('/workflow/<wfname>')
        @tokenize
        def update_workflow(wfname, **kwargs):
            formcontent = bottle.request.body.read()
            workflow = bson.json_util.loads(formcontent)['workflow']
            workflow_id = bson.json_util.ObjectId(workflow['_id'])
            workflow['_id'] = workflow_id
            wfstring = bson.json_util.dumps(workflow)
            return self.postRequest("/workflow", entity=wfname, data=wfstring,
                                    **kwargs)

        @b.delete('/workflow/<wfname>')
        @tokenize
        def delete_workflow(wfname, **kwargs):
            return self.deleteRequest("/workflow", entity=wfname, **kwargs)

        @b.route('/workflow')
        @b.route('/workflow/')
        @tokenize
        def get_workflow(**kwargs):
            return response(self.workflowRequest(**kwargs))

        @b.route('/workflow/<name>/rendered')
        @tokenize
        def get_rendered_workflow(name, **kwargs):
            res = self.workflowRequest(name, 'queue', **kwargs)
            if res['status'] == "success":
                task_summary = res['data']
            else:
                task_summary = []

            issue_objs = {}
            if (task_summary is not None and
                    'tasks' in task_summary and
                    len(task_summary['tasks']) > 0):
                for task in task_summary['tasks']:
                    if 'start' in task:
                        task['startDate'] = task['start'].\
                            strftime("%Y-%m-%d %H:%M")
                        starttz = task['start'].tzinfo
                        end_of_time = utc.localize(datetime.max).\
                            astimezone(starttz)
                        end_of_time_str = end_of_time.\
                            strftime("%Y-%m-%d %H:%M")
                        if task['startDate'] == end_of_time_str:
                            task['frozen'] = True
                        else:
                            task['frozen'] = False
                    else:
                        task['startDate'] = ""
                        task['frozen'] = False
                    task['updateDate'] = task['t'].\
                        strftime(format="%Y-%m-%d %H:%M")
                    res = self.issueRequest(str(task['iid']), **kwargs)
                    if res['status'] == "success":
                        issue = res['data']
                    else:
                        issue = None
                    if issue is not None:
                        issue_objs[str(task['iid'])] = issue['issue']['jira']

            hidden_done = {}
            cookie_hideDone = bottle.request.get_cookie('workflows_hide_done')
            # convert the octal
            if cookie_hideDone:
                cookie_hideDone = urlparse.unquote(cookie_hideDone)
                if cookie_hideDone and cookie_hideDone != "[]":
                    try:
                        tmp = bson.json_util.loads(cookie_hideDone)
                        for i in tmp:
                            hidden_done[i] = 1
                    except Exception as e:
                        self.logger.exception(e)
            if name in hidden_done:
                hide_done = True
            else:
                hide_done = False

            hidden_frozen = {}
            cookie_hideFrozen = bottle.request.\
                get_cookie('workflows_hide_frozen')
            # convert the octal
            if cookie_hideFrozen:
                cookie_hideFrozen = urlparse.unquote(cookie_hideFrozen)
                if cookie_hideFrozen and cookie_hideFrozen != "[]":
                    try:
                        tmp = bson.json_util.loads(cookie_hideFrozen)
                        for i in tmp:
                            hidden_frozen[i] = 1
                    except Exception as e:
                        self.logger.exception(e)
            if name in hidden_frozen:
                hide_frozen = True
            else:
                hide_frozen = False

            data = {'ticketSummary': task_summary, 'issues': issue_objs,
                    'hide_done': hide_done, 'hide_frozen': hide_frozen}
            return response(self.workflowRequest(name, **kwargs),
                            template="tasks_workflow", template_data=data)

        @b.route('/workflow/<workflow>/process')
        @tokenize
        def process_workflow(workflow, **kwargs):
            return response(self.workflowRequest(workflow, "process",
                                                 **kwargs))

        @b.route('/workflow/<workflow>/approve')
        @tokenize
        def approve_workflow(workflow, **kwargs):
            return response(self.workflowRequest(workflow, "approve",
                                                 **kwargs))

        @b.route('/workflow/<workflow>/disapprove')
        @tokenize
        def disapprove_workflow(workflow, **kwargs):
            return response(self.workflowRequest(workflow, "disapprove",
                                                 **kwargs))

        @b.route('/workflow/<workflow>/remove')
        @tokenize
        def remove_workflow(workflow, **kwargs):
            return response(self.workflowRequest(workflow, "remove", **kwargs))

        @b.route('/workflow/<workflow>/sleep/<seconds>')
        @tokenize
        def sleep_workflow(workflow, seconds, **kwargs):
            return response(self.workflowRequest(workflow, "sleep", seconds,
                                                 **kwargs))

        # AUTOCOMPLETE SEARCH
        @b.route('/search/<query>')
        def autocomplete(query):
            results = []
            if query is not None:
                results = g.search(query)
            return bson.json_util.dumps(results)

        # STATIC FILES
        @b.route('/js/<filename>')
        def server_js(filename):
            return bottle.static_file(filename, root="%s/js" %
                                      self.args['root_webdir'])

        @b.route('/css/<filename>')
        def server_css(filename):
            return bottle.static_file(filename, root="%s/css" %
                                      self.args['root_webdir'])

        @b.route('/img/<filename>')
        def server_img(filename):
            return bottle.static_file(filename, root="%s/img" %
                                      self.args['root_webdir'])

        self.logger.debug("start()")
        self.logger.info("euphonia!")

        b.run(host=self.args['euphonia_host'], port=self.args['euphonia_port'])

if __name__ == "__main__":
    parser = karakuricommon.karakuriclientparser(description="A euphoric "
                                                             "experience")
    parser.add_config_argument("--euphonia-host", metavar="HOSTNAME",
                               default="localhost",
                               help="specify the euphonia hostname "
                                    "(default=localhost)")
    parser.add_config_argument("--euphonia-port", metavar="PORT", type=int,
                               default=8070,
                               help="specify the euphonia port (default=8080)")
    parser.add_config_argument("--mongo-uri", metavar="MONGO",
                               default="mongodb://localhost:27017",
                               help="specify the MongoDB URI (default="
                               "mongodb://localhost:27017)")
    parser.add_config_argument("--pid", metavar="FILE",
                               default="/tmp/euphonia.pid",
                               help="specify a PID file "
                                    "(default=/tmp/euphonia.pid)")
    parser.add_config_argument("--root-webdir", metavar="DIRECTORY",
                               default="%s/web" % os.getcwd(),
                               help="specify the root web directory")
    parser.add_argument("command", choices=["start", "stop", "restart"],
                        help="<-- the available actions, choose one")

    args = parser.parse_args()

    # Lock it down
    pidfile = pidlockfile.PIDLockFile(args.pid)

    if args.command == "start":
        if pidfile.is_locked():
            print("There is already a running process")
            sys.exit(1)

    if args.command == "stop":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
            sys.exit(0)
        else:
            print("There is no running process to stop")
            sys.exit(2)

    if args.command == "restart":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
        else:
            print("There is no running process to stop")

    # Require a log file and preserve it while daemonized
    if args.log is None:
        print("Please specify a log file")
        sys.exit(3)

    logger = logging.getLogger("logger")
    fh = logging.FileHandler(args.log)
    fh.setLevel(args.log_level)
    formatter = logging.Formatter('%(asctime)s - %(module)s - '
                                  '%(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # This is daemon territory
    context = daemon.DaemonContext(pidfile=pidfile,
                                   stderr=fh.stream, stdout=fh.stream)
    context.files_preserve = [fh.stream]
    # TODO implment signal_map

    print("Starting...")

    with context:
        e = Euphonia(args)
        # redirect stderr and stdout
        # sys.__stderr__ = PipeToLogger(k.logger)
        # sys.__stdout__ = PipeToLogger(k.logger)
        e.start()

    sys.exit(0)

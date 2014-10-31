#!/usr/bin/env python

import bottle
import bson.json_util
import daemon
import karakuricommon
import logging
import os
import pidlockfile
import pymongo
import pytz
import signal
import sys

from datetime import datetime
from models import failedtests, groups, salesforce_client, tests
from pprint import pprint

utc = pytz.UTC

class euphonia(karakuricommon.karakuriclient):
    def __init__(self, *args, **kwargs):
        karakuricommon.karakuriclient.__init__(self, *args, **kwargs)

        # Initialize dbs and collections
        try:
            self.mongo = pymongo.MongoClient(self.args['mongo_host'],
                                             self.args['mongo_port'])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e

        self.db_euphonia = self.mongo.euphonia

    def start(self):
        g = groups.Groups(self.db_euphonia)
        t = tests.Tests(self.db_euphonia)
        failedTests = failedtests.FailedTests(self.db_euphonia)
        # sf = salesforce_client.Salesforce()

        b = bottle.Bottle(autojson=False)
        bottle.TEMPLATE_PATH.insert(0,'%s/views' % self.args['root_webdir'])

        def response(result, cookies=None):
            self.logger.debug("response(%s)", result)
            if result['status'] == "success":
                if cookies is not None:
                    for cookie in cookies:
                        try:
                            val = bson.json_util.dumps(cookie[1])
                        except Exception as e:
                            val = e
                        bottle.response.set_cookie(str(cookie[0]), val)
                bottle.response.status = 200
            elif result['status'] == "fail":
                bottle.response.status = 500
            elif result['status'] == "error":
                bottle.response.status = 400
            return bson.json_util.dumps(result)

        def tokenize(func):
            """ A decorator for bottle-route callback functions to pass
            auth_token cookies """
            def wrapped(*args, **kwargs):
                kwargs['token'] = bottle.request.get_cookie("auth_token")
                return func(*args, **kwargs)
            return wrapped

        @b.post('/login')
        def login():
            token = bottle.request.params.get('auth_token')
            res = self.postRequest("/login", data={'token':token})
            if res['status'] == 'success':
                user = res['data']
                cookies = [(prop,user[prop]) for prop in user]
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
            if query is not None:
                query = {"GroupName": query}
            if test is not None:
                query = {"failedTests.test": {"$in": [test]}}
            limit = 25
            if page == '':
                page = 1
            page = int(page)
            skip = (page - 1) * limit
            sort = [("priority", pymongo.DESCENDING)]
            tests_summary = g.get_failed_tests_summary(sort=sort,
                                                       skip=skip,
                                                       limit=limit,
                                                       query=query)
            return bottle.template('base_page', renderpage="summary",
                            groups=tests_summary['groups'], page=page,
                            count=tests_summary['count'], issue=test)

        @b.route('/group/<gid>')
        def get_group_summary(gid):
            group_summary = g.get_group_summary(gid)
            if group_summary is not None:
                return bottle.template('base_page', renderpage="group",
                                group=group_summary, descriptionCache=descriptionCache)
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
        def get_tests():
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
            print("bahbahbah")
            pprint(kwargs)
            res = self.queueRequest(**kwargs)
            if res['status'] == "success":
                task_summary = res['data']
            else:
                task_summary = None

            workflows = bottle.request.get_cookie('workflows')
            try:
                workflows = bson.json_util.loads(workflows)
            except Exception as e:
                workflows = e
            print("badsfafsadf")
            pprint(workflows)
            if workflows:
                res = self.workflowsRequest(workflows, **kwargs)
            else:
                res = self.workflowRequest(**kwargs)
            if res['status'] == "success":
                task_workflows = res['data']
            else:
                task_workflows = None
            if (task_workflows is not None and
                    'workflows' in task_workflows and
                    len(task_workflows['workflows']) > 0):
                task_workflows = task_workflows['workflows']
            else:
                task_workflows = []
            issue_objs = {}
            if (task_summary is not None and
                    'tasks' in task_summary and
                    len(task_summary['tasks']) > 0):
                task_summary = task_summary['tasks']
                for task in task_summary:
                    if 'start' in task:
                        task['startDate'] = task['start'].strftime("%Y-%m-%d %H:%M")
                        starttz = task['start'].tzinfo
                        end_of_time = utc.localize(datetime.max).astimezone(starttz)
                        end_of_time_str = end_of_time.strftime("%Y-%m-%d %H:%M")
                        if task['startDate'] == end_of_time_str:
                            task['frozen'] = True
                        else:
                            task['frozen'] = False
                    else:
                        task['startDate'] = ""
                        task['frozen'] = False
                    task['updateDate'] = task['t'].strftime(format="%Y-%m-%d %H:%M")
                    res = self.issueRequest(str(task['iid']), **kwargs)
                    if res['status'] == "success":
                        issue = res['data']
                    else:
                        issue = None
                    print issue
                    if issue is not None:
                        issue_objs[str(task['iid'])] = issue['issue']['jira']
            else:
                task_summary = []
            return bottle.template('base_page', renderpage="tasks",
                            ticketSummary=task_summary, issues=issue_objs,
                            ticketWorkflows=task_workflows)

        @b.route('/task/<task>/process')
        def process_task(task):
            return response(self.taskRequest(task, "process"))

        @b.route('/task/<task>/approve')
        def approve_task(task):
            return response(self.taskRequest(task, "approve"))

        @b.route('/task/<task>/disapprove')
        def disapprove_task(task):
            return response(self.taskRequest(task, "disapprove"))

        @b.route('/task/<task>/remove')
        def remove_task(task):
            return response(self.taskRequest(task, "remove"))

        @b.route('/task/<task>/sleep')
        def freeze_task(task):
            return response(self.taskRequest(task, "sleep"))

        @b.route('/task/<task>/wake')
        def wake_task(task):
            return response(self.taskRequest(task, "sleep"))

        @b.route('/task/<task>/sleep/<seconds>')
        def sleep_task(task, seconds):
            seconds = int(seconds)
            return response(self.taskRequest(task, "sleep", seconds))

        @b.route('/workflows')
        def edit_workflows():
            return bottle.template('base_page', renderpage="workflows")

        @b.post('/testworkflow')
        def test_workflow():
            formcontent = bottle.request.body.read()
            if 'workflow' in formcontent:
                workflow = bson.json_util.loads(formcontent)['workflow']
                wfstring = bson.json_util.dumps(workflow)
                print wfstring
                res = self.postRequest("testworkflow", data=wfstring)
                if res['status'] == "success":
                    if 'data' in res and 'issues' in res['data']:
                        for issue in res['data']['issues']:
                            del issue['jira']['changelog']
                            del issue['jira']['fields']['comment']
                            del issue['jira']['fields']['attachment']
                            if 'karakuri' in issue and 'sleep' in issue['karakuri']:
                                del issue['karakuri']['sleep']
                    return bson.json_util.dumps(res)
                else:
                    return res
            msg = {"status": "error",
                   "message": "workflow missing 'query_string'"}
            return bson.json_util.dumps(msg)

        @b.post('/workflow')
        def create_workflow():
            formcontent = bottle.request.body.read()
            workflow = bson.json_util.loads(formcontent)['workflow']
            wfstring = bson.json_util.dumps(workflow)
            return self.postRequest("workflow", data=wfstring)

        @b.post('/workflow/<wfname>')
        def update_workflow(wfname):
            formcontent = bottle.request.body.read()
            workflow = bson.json_util.loads(formcontent)['workflow']
            workflow_id = bson.json_util.ObjectId(workflow['_id'])
            workflow['_id'] = workflow_id
            wfstring = bson.json_util.dumps(workflow)
            return self.postRequest("workflow", entity=wfname, data=wfstring)

        @b.delete('/workflow/<wfname>')
        def delete_workflow(wfname):
            return self.deleteRequest("/workflow", entity=wfname)

        @b.route('/workflow')
        @b.route('/workflow/')
        def get_workflows():
            return response(self.workflowRequest())

        @b.route('/workflow/<workflow>/process')
        def process_workflow(workflow):
            return response(self.workflowRequest(workflow, "process"))

        @b.route('/workflow/<workflow>/approve')
        def approve_workflow(workflow):
            return response(self.workflowRequest(workflow, "approve"))

        @b.route('/workflow/<workflow>/disapprove')
        def disapprove_workflow(workflow):
            return response(self.workflowRequest(workflow, "disapprove"))

        @b.route('/workflow/<workflow>/remove')
        def remove_workflow(workflow):
            return response(self.workflowRequest(workflow, "remove"))

        @b.route('/workflow/<workflow>/sleep/<seconds>')
        def sleep_workflow(workflow, seconds):
            return response(self.workflowRequest(workflow, "sleep", seconds))

        # AUTOCOMPLETE SEARCH
        @b.route('/search/<query>')
        def autocomplete(query):
            results = []
            if query is not None:
                results = g.search(query)
            return json.dumps(results)

        # STATIC FILES
        @b.route('/js/<filename>')
        def server_js(filename):
            return bottle.static_file(filename, root="%s/js" % self.args['root_webdir'])

        @b.route('/css/<filename>')
        def server_css(filename):
            return bottle.static_file(filename, root="%s/css" % self.args['root_webdir'])

        @b.route('/img/<filename>')
        def server_img(filename):
            return bottle.static_file(filename, root="%s/img" % self.args['root_webdir'])

        self.logger.debug("start()")
        self.logger.info("euphonia!")

        b.run(host=self.args['euphonia_host'], port=self.args['euphonia_port'])

if __name__ == "__main__":
    parser = karakuricommon.karakuriclientparser(description="A euphoric "
                                                             "experience")
    parser.add_config_argument("--euphonia-host", metavar="HOSTNAME",
                               default="localhost",
                                help="specify the euphonia hostname (default=localhost)")
    parser.add_config_argument("--euphonia-port", metavar="PORT", type=int,
                               default=8070,
                               help="specify the euphonia port (default=8080)")
    parser.add_config_argument("--mongo-host", metavar="HOSTNAME",
                               default="localhost",
                               help="specify the MongoDB hostname (default="
                                    "localhost)")
    parser.add_config_argument("--mongo-port", metavar="PORT", default=27017,
                               type=int,
                               help="specify the MongoDB port (default=27017)")
    parser.add_config_argument("--pid", metavar="FILE",
                               default="/tmp/euphonia.pid",
                               help="specify a PID file "
                                    "(default=/tmp/euphonia.pid)")
    parser.add_config_argument("--root-webdir", metavar="DIRECTORY",
                               default=".",
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
        e = euphonia(args)
        # redirect stderr and stdout
        # sys.__stderr__ = PipeToLogger(k.logger)
        # sys.__stdout__ = PipeToLogger(k.logger)
        e.start()

    sys.exit(0)

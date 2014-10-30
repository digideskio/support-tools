#!/usr/bin/env python

import daemon
import karakuricommon
import logging
import os
import signal
import sys
import json
import pidlockfile
from datetime import datetime

import pymongo
import pytz
from bson import json_util

from bottle import redirect, request, template, static_file, Bottle, TEMPLATE_PATH
from models import failedtests, salesforce_client, tests, groups

utc = pytz.UTC

class euphonia(karakuricommon.karakuriclient):
    def __init__(self, *args, **kwargs):
        karakuricommon.karakuriclient.__init__(self, *args, **kwargs)

    def run(self):
        mongodb_connection_string = "mongodb://localhost"
        connection = pymongo.MongoClient(mongodb_connection_string)
        euphoniaDB = connection.euphonia

        g = groups.Groups(euphoniaDB)
        t = tests.Tests(euphoniaDB)
        failedTests = failedtests.FailedTests(euphoniaDB)

        # sf = salesforce_client.Salesforce()
        app = Bottle()
        TEMPLATE_PATH.insert(0,'%s/views' % self.args['root_webdir'])

        @app.hook('before_request')
        def before_request():
            if not self.getToken() and request.get_cookie("auth_token"):
                self.setToken(request.get_cookie("auth_token"));

        # ROOT/SUMMARY PAGE
        @app.route('/')
        def index():
            return redirect('/tasks')

        # GROUP-RELATED ROUTES
        @app.route('/groups/<page>/<query>')
        @app.route('/groups/page/<page>')
        @app.route('/groups')
        @app.route('/groups/')
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
            return template('base_page', renderpage="summary",
                            groups=tests_summary['groups'], page=page,
                            count=tests_summary['count'], issue=test)

        @app.route('/group/<gid>')
        def get_group_summary(gid):
            group_summary = g.get_group_summary(gid)
            if group_summary is not None:
                return template('base_page', renderpage="group",
                                group=group_summary, descriptionCache=descriptionCache)
            else:
                return redirect('/groups')

        @app.route('/group/<gid>/ignore/<test>')
        def ignore_test(gid, test):
            g.ignore_test(gid, test)
            return redirect('/group/%s' % gid)

        @app.route('/group/<gid>/include/<test>')
        def include_test(gid, test):
            g.include_test(gid, test)
            return redirect('/group/%s' % gid)

        # TEST-RELATED ROUTES
        @app.route('/tests')
        def get_failed_tests_summary():
            return template('base_page', renderpage="tests")

        @app.route('/test')
        def get_tests():
            tobj = t.get_tests()
            output = {"status": "success", "data": {"tests": tobj}}
            return json_util.dumps(output)

        @app.route('/defined_tests')
        def get_tests():
            tobj = t.get_defined_tests()
            output = {"status": "success", "data": {"defined_tests": tobj}}
            return json_util.dumps(output)

        @app.route('/test/<test>')
        def get_matching_groups(test):
            if test is not None:
                query = {"failedTests.test": test}
                tobj = g.get_failed_tests_summary(sort=[
                    ("priority", pymongo.DESCENDING),
                    ("GroupName", pymongo.ASCENDING)],
                    skip=0, limit=10, query=query)
                output = {"status": "success", "data": tobj}
                return json_util.dumps(output)
            else:
                output = {"status": "success", "data": {}}
                return json_util.dumps(output)

        @app.post('/test')
        def create_test():
            formcontent = request.body.read()
            test = json_util.loads(formcontent)['test']
            return json_util.dumps(t.create_test(test))

        @app.post('/test/<test_name>')
        def update_test(test_name):
            formcontent = request.body.read()
            test = json_util.loads(formcontent)['test']
            test_id = json_util.ObjectId(test['_id'])
            test['_id'] = test_id
            return json_util.dumps(t.update_test(test_name, test))

        @app.delete('/test/<test_name>')
        def delete_test(test_name):
            return json_util.dumps(t.delete_test(test_name))

        # ISSUE ROUTES
        @app.route('/tasks')
        def issue_summary():
            res = self.queueRequest()
            if res['status'] == "success":
                task_summary = res['data']
            else:
                task_summary = None
            res = self.workflowRequest()
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
                    res = self.issueRequest(str(task['iid']))
                    if res['status'] == "success":
                        issue = res['data']
                    else:
                        issue = None
                    print issue
                    if issue is not None:
                        issue_objs[str(task['iid'])] = issue['issue']['jira']
            else:
                task_summary = []
            return template('base_page', renderpage="tasks",
                            ticketSummary=task_summary, issues=issue_objs,
                            ticketWorkflows=task_workflows)

        @app.route('/task/<task>/process')
        def process_task(task):
            return json_util.dumps(self.taskRequest(task, "process"))

        @app.route('/task/<task>/approve')
        def approve_task(task):
            return json_util.dumps(self.taskRequest(task, "approve"))

        @app.route('/task/<task>/disapprove')
        def disapprove_task(task):
            return json_util.dumps(self.taskRequest(task, "disapprove"))

        @app.route('/task/<task>/remove')
        def remove_task(task):
            return json_util.dumps(self.taskRequest(task, "remove"))

        @app.route('/task/<task>/sleep')
        def freeze_task(task):
            return json_util.dumps(self.taskRequest(task, "sleep"))

        @app.route('/task/<task>/wake')
        def wake_task(task):
            return json_util.dumps(self.taskRequest(task, "sleep"))

        @app.route('/task/<task>/sleep/<seconds>')
        def sleep_task(task, seconds):
            seconds = int(seconds)
            return json_util.dumps(self.taskRequest(task, "sleep", seconds))

        @app.route('/workflows')
        def edit_workflows():
            return template('base_page', renderpage="workflows")

        @app.post('/testworkflow')
        def test_workflow():
            formcontent = request.body.read()
            if 'workflow' in formcontent:
                workflow = json_util.loads(formcontent)['workflow']
                wfstring = json_util.dumps(workflow)
                print wfstring
                res = self.postRequest("testworkflow", data=wfstring)
                if res['status'] == "success":
                    if 'data' in response and 'issues' in response['data']:
                        for issue in response['data']['issues']:
                            del issue['jira']['changelog']
                            del issue['jira']['fields']['comment']
                            del issue['jira']['fields']['attachment']
                            if 'karakuri' in issue and 'sleep' in issue['karakuri']:
                                del issue['karakuri']['sleep']
                    return json_util.dumps(response)
                else:
                    return res
            msg = {"status": "error",
                   "message": "workflow missing 'query_string'"}
            return json_util.dumps(msg)

        @app.post('/workflow')
        def create_workflow():
            formcontent = request.body.read()
            workflow = json_util.loads(formcontent)['workflow']
            wfstring = json_util.dumps(workflow)
            return self.postRequest("workflow", data=wfstring)

        @app.post('/workflow/<wfname>')
        def update_workflow(wfname):
            formcontent = request.body.read()
            workflow = json_util.loads(formcontent)['workflow']
            workflow_id = json_util.ObjectId(workflow['_id'])
            workflow['_id'] = workflow_id
            wfstring = json_util.dumps(workflow)
            return self.postRequest("workflow", entity=wfname, data=wfstring)

        @app.delete('/workflow/<wfname>')
        def delete_workflow(wfname):
            return self.deleteRequest("/workflow", entity=wfname)

        @app.route('/workflow')
        @app.route('/workflow/')
        def get_workflows():
            res = self.workflowRequest()
            if res['status'] == "success":
                workflows = res['data']
            else:
                workflows = None
            return json_util.dumps(workflows)

        @app.route('/workflow/<workflow>/process')
        def process_workflow(workflow):
            return self.workflowRequest(workflow, "process")

        @app.route('/workflow/<workflow>/approve')
        def approve_workflow(workflow):
            return self.workflowRequest(workflow, "approve")

        @app.route('/workflow/<workflow>/disapprove')
        def disapprove_workflow(workflow):
            return self.workflowRequest(workflow, "disapprove")

        @app.route('/workflow/<workflow>/remove')
        def remove_workflow(workflow):
            return self.workflowRequest(workflow, "remove")

        @app.route('/workflow/<workflow>/sleep/<seconds>')
        def sleep_workflow(workflow, seconds):
            return self.workflowRequest(workflow, "sleep", seconds)

        # AUTOCOMPLETE SEARCH
        @app.route('/search/<query>')
        def autocomplete(query):
            results = []
            if query is not None:
                results = g.search(query)
            return json.dumps(results)

        # STATIC FILES
        @app.route('/js/<filename>')
        def server_js(filename):
            return static_file(filename, root="%s/js" % self.args['root_webdir'])

        @app.route('/css/<filename>')
        def server_css(filename):
            return static_file(filename, root="%s/css" % self.args['root_webdir'])

        @app.route('/img/<filename>')
        def server_img(filename):
            return static_file(filename, root="%s/img" % self.args['root_webdir'])

        self.logger.debug("start()")
        self.logger.info("euphonia!")

        app.run(host=self.args['euphonia_host'], port=self.args['euphonia_port'])

if __name__ == "__main__":
    parser = karakuricommon.karakuriclientparser(description="A euphoric "
                                                             "experience")
    parser.add_config_argument("--euphonia-host", metavar="HOSTNAME",
                               default="localhost",
                                help="specify the euphonia hostname (default=localhost)")
    parser.add_config_argument("--euphonia-port", metavar="PORT", type=int,
                               default=8070,
                               help="specify the euphonia port (default=8080)")
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
        e.run()

    mongodb_connection_string = "mongodb://localhost"
    connection = pymongo.MongoClient(mongodb_connection_string)
    euphoniaDB = connection.euphonia

    g = groups.Groups(euphoniaDB)
    t = tests.Tests(euphoniaDB)
    failedTests = failedtests.FailedTests(euphoniaDB)

    # sf = salesforce_client.Salesforce()

    sys.exit(0)

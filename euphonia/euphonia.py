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
import urlparse

from datetime import datetime
from models import groups, salesforce_client, tests

utc = pytz.UTC


class Euphonia(karakuricommon.karakuriclient):
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
        # sf = salesforce_client.Salesforce()

        # TODO clean this up
        descriptionCache = {
                "greeting" : "Hi",
                "opening" : "In reviewing your MongoDB configuration data in MMS, we have identified an issue that should be addressed in order to avoid potentially-critical issues in the future. In particular:",
                "closing" : "We look forward to working with you to resolve this issues described above, and we have created individual support tickets to track each issue (you should receive notifications shortly). Please review any tickets at your earliest convenience so we can schedule some time to work with you.<br/><br/>Thanks,<br/>The MongoDB Proactive Services Team"
        }
        # populate descriptionCache
        curr_tests = self.db_euphonia.mmsgroupreporttests.find({})
        if curr_tests is not None:
            for test in curr_tests:
                descriptionCache[test['name']] = test['comment']

        b = bottle.Bottle(autojson=False)

        bottle.TEMPLATE_PATH.insert(0, '%s/views' % self.args['root_webdir'])

        def response(result, cookies=None, template=None, template_data=None):
            self.logger.debug("response(%s,%s,%s,%s)", result, cookies, template, template_data)
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
                                       group=group_summary,
                                       descriptionCache=descriptionCache)
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
            # list of workflows
            res = self.workflowRequest(**kwargs)
            if res['status'] == "success":
                workflows = res['data']['workflows']
            else:
                workflows = []

            workflowMap = {workflow['name']:workflow for workflow in workflows}
            workflowNames = workflowMap.keys()
            workflowNames.sort()

            user_workflows = []
            cookie_workflowNames = bottle.request.get_cookie('workflows')

            # convert the octal
            if cookie_workflowNames:
                cookie_workflowNames = urlparse.unquote(cookie_workflowNames)
                if cookie_workflowNames and cookie_workflowNames != "[]":
                    try:
                        user_workflows = bson.json_util.loads(cookie_workflowNames)
                        user_workflows.sort()
                    except Exception as e:
                        self.logger.exception(e)


            content = ''
            for workflow in user_workflows:
                content += get_rendered_workflow(workflow, **kwargs)
            return bottle.template('base_page', renderpage="tasks", allWorkflows=workflowNames, content=content)

        @b.route('/task/<task>/process')
        @tokenize
        def process_task(task, **kwargs):
            return response(self.taskRequest(task, "process", **kwargs))

        @b.route('/task/<task>/approve')
        @tokenize
        def approve_task(task, **kwargs):
            ret = self.taskRequest(task, "approve")
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
            res = self.postRequest("/user/%s/workflow/%s" % (uid, workflow), **kwargs)
            return bson.json_util.dumps(res)

        @b.delete('/user/<uid>/workflow/<workflow>')
        @tokenize
        def user_remove_workflow(uid, workflow, **kwargs):
            """ Remove user workflow """
            res = self.deleteRequest("/user/%s/workflow/%s" % (uid, workflow), **kwargs)
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
                res = self.postRequest("/testworkflow", data=wfstring, **kwargs)
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
            return self.postRequest("/workflow", entity=wfname, data=wfstring, **kwargs)

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
            cookie_hideFrozen = bottle.request.get_cookie('workflows_hide_frozen')
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

            data = {'ticketSummary': task_summary, 'issues': issue_objs, 'hide_done': hide_done, 'hide_frozen': hide_frozen}
            return response(self.workflowRequest(name, **kwargs), template="tasks_workflow", template_data=data)

        @b.route('/workflow/<workflow>/process')
        @tokenize
        def process_workflow(workflow, **kwargs):
            return response(self.workflowRequest(workflow, "process", **kwargs))

        @b.route('/workflow/<workflow>/approve')
        @tokenize
        def approve_workflow(workflow, **kwargs):
            return response(self.workflowRequest(workflow, "approve", **kwargs))

        @b.route('/workflow/<workflow>/disapprove')
        @tokenize
        def disapprove_workflow(workflow, **kwargs):
            return response(self.workflowRequest(workflow, "disapprove", **kwargs))

        @b.route('/workflow/<workflow>/remove')
        @tokenize
        def remove_workflow(workflow, **kwargs):
            return response(self.workflowRequest(workflow, "remove", **kwargs))

        @b.route('/workflow/<workflow>/sleep/<seconds>')
        @tokenize
        def sleep_workflow(workflow, seconds, **kwargs):
            return response(self.workflowRequest(workflow, "sleep", seconds, **kwargs))

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

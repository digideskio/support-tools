#!/usr/bin/env python

import logging
import sys
import json
from datetime import datetime

import pymongo
import pytz
from bson import json_util

from daemon import Daemon
from bottle import redirect, request, template, static_file, Bottle
from models import karakuri_client, failedtests,\
    salesforce_client, tests, groups


utc = pytz.UTC
app = Bottle()


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
    try:
        task_summary = karakuri.get_queues()['data']
    except RuntimeError:
        task_summary = None
    try:
        task_workflows = karakuri.get_workflows()['data']
    except RuntimeError:
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
            issue = karakuri.get_issue(str(task['iid']))
            print issue
            if issue is not None and 'data' in issue:
                issue_objs[str(task['iid'])] = issue['data']['issue']['jira']
    else:
        task_summary = []
    return template('base_page', renderpage="tasks",
                    ticketSummary=task_summary, issues=issue_objs,
                    ticketWorkflows=task_workflows)


@app.route('/task/<task>/process')
def process_task(task):
    return json_util.dumps(karakuri.process_task(task))


@app.route('/task/<task>/approve')
def approve_task(task):
    return json_util.dumps(karakuri.approve_task(task))


@app.route('/task/<task>/disapprove')
def disapprove_task(task):
    return json_util.dumps(karakuri.disapprove_task(task))


@app.route('/task/<task>/remove')
def remove_task(task):
    return json_util.dumps(karakuri.remove_task(task))


@app.route('/task/<task>/sleep')
def freeze_task(task):
    return json_util.dumps(karakuri.sleep_task(task))


@app.route('/task/<task>/wake')
def wake_task(task):
    return json_util.dumps(karakuri.wake_task(task))


@app.route('/task/<task>/sleep/<seconds>')
def sleep_task(task, seconds):
    seconds = int(seconds)
    return json_util.dumps(karakuri.sleep_task(task, seconds))


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
        response = karakuri.test_workflow(wfstring)
        if 'data' in response and 'issues' in response['data']:
            for issue in response['data']['issues']:
                del issue['jira']['changelog']
                del issue['jira']['fields']['comment']
                del issue['jira']['fields']['attachment']
                if 'karakuri' in issue and 'sleep' in issue['karakuri']:
                    del issue['karakuri']['sleep']
        return json_util.dumps(response)
    else:
        msg = {"status": "error",
               "message": "workflow missing 'query_string'"}
        return json_util.dumps(msg)


@app.post('/workflow')
def create_workflow():
    formcontent = request.body.read()
    workflow = json_util.loads(formcontent)['workflow']
    wfstring = json_util.dumps(workflow)
    return json_util.dumps(karakuri.create_workflow(wfstring))


@app.post('/workflow/<wfname>')
def update_workflow(wfname):
    formcontent = request.body.read()
    workflow = json_util.loads(formcontent)['workflow']
    workflow_id = json_util.ObjectId(workflow['_id'])
    workflow['_id'] = workflow_id
    wfstring = json_util.dumps(workflow)
    return json_util.dumps(karakuri.update_workflow(wfname, wfstring))


@app.delete('/workflow/<wfname>')
def delete_workflow(wfname):
    return json_util.dumps(karakuri.delete_workflow(wfname))


@app.route('/workflow')
@app.route('/workflow/')
def get_workflows():
    workflows = karakuri.get_workflows()
    return json_util.dumps(workflows)


@app.route('/workflow/<workflow>/process')
def process_workflow(workflow):
    return karakuri.process_workflow(workflow)


@app.route('/workflow/<workflow>/approve')
def approve_workflow(workflow):
    return karakuri.approve_workflow(workflow)


@app.route('/workflow/<workflow>/disapprove')
def disapprove_workflow(workflow):
    return karakuri.delete_workflow(workflow)


@app.route('/workflow/<workflow>/remove')
def remove_workflow(workflow):
    return karakuri.remove_workflow(workflow)


@app.route('/workflow/<workflow>/sleep/<days>')
def sleep_workflow(workflow, days):
    return karakuri.sleep_workflow(workflow, days)


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
    return static_file(filename, root='./js')


@app.route('/css/<filename>')
def server_css(filename):
    return static_file(filename, root='./css')


@app.route('/img/<filename>')
def server_img(filename):
    return static_file(filename, root='./img')


class Automaton(Daemon):
    def run(self):
        app.run(host='0.0.0.0', port=8070)

if __name__ == "__main__":
    logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.INFO)
    logging.info("Initializing Euphonia UI")

    mongodb_connection_string = "mongodb://localhost"
    karakuri_connection_string = "http://localhost:8080"

    descriptionJSON = open('descriptions.json')
    descriptionCache = json.load(descriptionJSON)
    descriptionJSON.close()

    connection = pymongo.MongoClient(mongodb_connection_string)
    euphoniaDB = connection.euphonia
    supportDB = connection.support

    karakuri = karakuri_client.Karakuri(karakuri_connection_string)
    g = groups.Groups(euphoniaDB)
    t = tests.Tests(euphoniaDB)
    failedTests = failedtests.FailedTests(euphoniaDB)

    # sf = salesforce_client.Salesforce()

    daemon = Automaton('euphonia.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
                daemon.stop()
        elif 'restart' == sys.argv[1]:
                daemon.restart()
        else:
                print "Unknown command"
                sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        daemon.run()
        sys.exit(2)

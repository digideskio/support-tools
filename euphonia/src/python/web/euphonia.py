#!/usr/bin/env python

from bottle import run, redirect, post, request, error, route, template, static_file, Bottle
import pymongo
import logging
import sys
import json
import pytz
from datetime import datetime
import failedTestDAO
import groupDAO
import issueDAO
import ticketDAO
import karakuriDAO
import salesforceDAO
from daemon import Daemon
from bson import json_util

utc = pytz.UTC
app = Bottle()

@app.route('/test')
def getContacts():
    return sf.getContacts()

# ROOT/SUMMARY PAGE
@app.route('/<page:re:\d*>')
def index(page=1):
    return redirect('/'.join(['/groups',page]))

# GROUP-RELATED ROUTES
@app.route('/groups/<page:re:\d*>/<query>')
@app.route('/groups')
@app.route('/groups/')
@app.route('/test/<test>')
def groups(page=1, test=None, query=None):
    query = None
    if query is not None:
        query = {"GroupName": query}
    if test is not None:
        query = {"failedTests.test":{"$in":[test]}}
    limit = 25
    if page == '':
        page = 1
    page = int(page)
    skip = (page - 1) * limit
    sortField = 'priority'
    order = pymongo.DESCENDING
    testsSummary = groups.getFailedTestsSummary(sortField=sortField, order=order, skip=skip, limit=limit, query=query)
    return template('base_page', renderpage="summary", groups=testsSummary['groups'], page=page, count=testsSummary['count'], issue=test)

@app.route('/group/<gid>')
def groupSummary(gid):
    groupSummary = groups.getGroupSummary(gid)
    if groupSummary is not None:
        return template('base_page', renderpage="group", group=groupSummary, descriptionCache=descriptionCache)
    else:
        return redirect('/groups')

@app.route('/group/<gid>/ignore/<test>')
def ignoreTest(gid, test):
    groups.ignoreTest(gid, test)
    return redirect('/group/%s' % gid)

@app.route('/group/<gid>/include/<test>')
def includeTest(gid, test):
    groups.includeTest(gid, test)
    return redirect('/group/%s' % gid)

#FAILEDTEST-RELATED ROUTES
@app.route('/tests')
def failedTestsSummary():
    failedTestsSummary = failedTests.getFailedTestsSummary()
    topFailedTests = failedTests.getTopFailedTests(5)
    return template('base_page', renderpage="tests", testSummary=failedTestsSummary, topTests=topFailedTests, descriptionCache=descriptionCache)

#ISSUE ROUTES
@app.route('/issues')
def issueSummary(workflow=None, page=1):
    query = None
    if workflow is not None:
        query = {"workflow": {"$in": [workflow]}}
    limit = 25
    if page == '':
        page = 1
    page = int(page)
    ticketSummary = karakuri.getQueues()
    ticketWorkflows = karakuri.getWorkflows()
    if ticketWorkflows is not None and 'workflows' in ticketWorkflows and len(ticketWorkflows['workflows']) > 0:
        ticketWorkflows = ticketWorkflows['workflows']
    else:
        ticketWorkflows = []
    issueObjs = {}
    if ticketSummary is not None and 'tasks' in ticketSummary and len(ticketSummary['tasks']) > 0:
        ticketSummary = ticketSummary['tasks']
        for ticket in ticketSummary:
            if 'start' in ticket:
                ticket['startDate'] = datetime.strftime(ticket['start'], "%Y-%m-%d %H:%M")
                starttz = ticket['start'].tzinfo
                endOfTime = utc.localize(datetime.max).astimezone(starttz)
                endOfTimeStr = datetime.strftime(endOfTime, "%Y-%m-%d %H:%M")
                ticket['frozen'] = True if ticket['startDate'] == endOfTimeStr else False
            else:
                ticket['startDate'] = ""
                ticket['frozen'] = False
            ticket['updateDate'] = datetime.strftime(ticket['t'], "%Y-%m-%d %H:%M")
            issue = karakuri.getIssue(str(ticket['iid']))
            print issue
            if issue is not None and 'issue' in issue:
                issueObjs[str(ticket['iid'])] = issue['issue']['jira']
    else:
        ticketSummary = []
    return template('base_page', renderpage="tickets", ticketSummary=ticketSummary, issues=issueObjs, ticketWorkflows=ticketWorkflows)

@app.route('/task/<task>/process')
def processTicket(task):
    return json_util.dumps(karakuri.processTicket(task))

@app.route('/task/<task>/approve')
def approveTicket(task):
    return json_util.dumps(karakuri.approveTicket(task))

@app.route('/task/<task>/disapprove')
def disapproveTicket(task):
    return json_util.dumps(karakuri.disapproveTicket(task))

@app.route('/task/<task>/remove')
def removeTicket(task):
    return json_util.dumps(karakuri.removeTicket(task))

@app.route('/task/<task>/sleep')
def delayTicket(task):
    return json_util.dumps(karakuri.sleepTicket(task))

@app.route('/task/<task>/wake')
def wakeTicket(task):
    return json_util.dumps(karakuri.wakeTicket(task))

@app.route('/task/<task>/sleep/<seconds>')
def delayTicket(task, seconds):
    seconds = int(seconds)
    return json_util.dumps(karakuri.sleepTicket(task, seconds))

@app.route('/workflows')
def editWorkflows():
    return template('base_page', renderpage="workflows")

@app.post('/workflow')
def createWorkflow():
    formcontent = request.body.read()
    workflow = json_util.loads(formcontent)['workflow']
    print workflow
    return json_util.dumps(karakuri.createWorkflow(json_util.dumps(workflow)))

@app.post('/workflow/<wfname>')
def updateWorkflow(wfname):
    formcontent = request.body.read()
    workflow = json_util.loads(formcontent)['workflow']
    workflowId = json_util.ObjectId(workflow['_id'])
    workflow['_id'] = workflowId
    print workflow
    return json_util.dumps(karakuri.updateWorkflow(wfname, json_util.dumps(workflow)))

@app.route('/workflow')
@app.route('/workflow/')
def getWorkflows():
    return json_util.dumps(karakuri.getWorkflows())

@app.route('/workflow/<workflow>/process')
def processWorkflow(workflow):
    return karakuri.processWorkflow(workflow)

@app.route('/workflow/<workflow>/approve')
def approveWorkflow(workflow):
    return karakuri.approveWorkflow(workflow)

@app.route('/workflow/<workflow>/disapprove')
def disapproveWorkflow(workflow):
    return karakuri.disapproveWorkflow(workflow)

@app.route('/workflow/<workflow>/remove')
def removeWorkflow(workflow):
    return karakuri.removeWorkflow(workflow)

@app.route('/workflow/<workflow>/sleep/<days>')
def delayWorkflow(workflow, days):
    return karakuri.sleepWorkflow(workflow, days)

# AUTOCOMPLETE SEARCH
@app.route('/search/<query>')
def autocomplete(query):
    results = []
    if query is not None:
        results = groups.search(query)
    return json.dumps(results)

# STATIC FILES
@app.route('/js/<filename>')
def server_js(filename):
    return static_file(filename, root='./js')

@app.route('/css/<filename>')
def server_css(filename):
    return static_file(filename, root='./css')

@app.route('/img/<filename>')
def server_css(filename):
    return static_file(filename, root='./img')

class automaton(Daemon):
    def run(self):
        app.run(host='0.0.0.0', port=8070)

if __name__ == "__main__":
    logging.basicConfig(format='[%(asctime)s] %(message)s',level=logging.INFO)
    logging.info("Initializing Euphonia UI")

    mongodb_connection_string = "mongodb://localhost"
    karakuri_connection_string = "http://localhost:8080"

    descriptionJSON = open('descriptions.json')
    descriptionCache = json.load(descriptionJSON)
    descriptionJSON.close()

    connection = pymongo.MongoClient(mongodb_connection_string)
    euphoniaDB = connection.euphonia
    supportDB = connection.support

    karakuri = karakuriDAO.karakuriDAO(karakuri_connection_string)
    groups = groupDAO.GroupDAO(euphoniaDB)
    failedTests = failedTestDAO.FailedTestDAO(euphoniaDB)
    issues = issueDAO.IssueDAO(supportDB)
    tickets = ticketDAO.TicketDAO(karakuri)

    sf = salesforceDAO.salesforceDAO()

    daemon = automaton('euphonia.pid')
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
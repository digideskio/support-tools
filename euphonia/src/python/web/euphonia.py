#!/usr/bin/env python

from bottle import run, redirect, error, route, template, static_file, Bottle
import pymongo
import logging
import sys
import json
import failedTestDAO
import groupDAO
import issueDAO
import ticketDAO
import karakuriDAO
from daemon import Daemon

app = Bottle()

# ROOT/SUMMARY PAGE
@app.route('/<page:re:\d*>')
def index(page=1):
    return redirect('/'.join(['/groups',page]))

# GROUP-RELATED ROUTES
@app.route('/groups/<page:re:\d*>')
@app.route('/groups')
@app.route('/test/<test>')
def groups(page=1, test=None):
    query = None
    if test is not None:
        query = {"failedTests.test":{"$in":[test]}}
    limit = 10
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
    if workflow != None:
        query = {"workflow":{"$in":[workflow]}}
    limit = 10
    if page == '':
        page = 1
    page = int(page)
    skip = (page - 1) * limit
    sortField = 'priority'
    order = pymongo.DESCENDING
    #ticketSummary = tickets.getTicketSummary(query, sortField, order, skip, limit)
    ticketSummary = karakuri.getQueues()
    ticketWorkflows = karakuri.getWorkflows()
    print ticketWorkflows
    issueObjs = {}
    for issue in ticketSummary:
        issueObjs[str(issue['iid'])] = karakuri.getTicket(str(issue['iid']))['jira']
    return template('base_page', renderpage="tickets", ticketSummary=ticketSummary, issues=issueObjs, ticketWorkflows=ticketWorkflows)

@app.route('/ticket/<issue>/approve')
def approveIssue(issue):
    tickets.approveTicket(issue)
    karakuri.approveTicket(issue)
    return redirect('/issues')

@app.route('/ticket/<issue>/delay/<days>')
def delayIssue(issue,days):
    tickets.delayTicket(issue,days)
    return redirect('/issues')

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
    karakuri_connection_string = "http://localhost:8090"

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
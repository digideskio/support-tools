from bottle import run, redirect, error, route, template, static_file
import pymongo
import os
import json
import failedTestDAO
import groupDAO
import issueDAO
import ticketDAO

# ROOT/SUMMARY PAGE
@route('/<page:re:\d*>')
def index(page=1):
    return redirect('/'.join(['/groups',page]))

# GROUP-RELATED ROUTES
@route('/groups/<page:re:\d*>')
@route('/groups')
@route('/issue/<test>')
def groups(page=1, test=None):
    query = None
    if test is not None:
        query = {"failedTests.test":{"$in":[test]}}
    print query
    limit = 10
    if page == '':
        page = 1
    page = int(page)
    skip = (page - 1) * limit
    sortField = 'priority'
    order = pymongo.DESCENDING
    testsSummary = groups.getFailedTestsSummary(sortField=sortField, order=order, skip=skip, limit=limit, query=query)
    return template('base_page', renderpage="summary", groups=testsSummary['groups'], page=page, count=testsSummary['count'], issue=test)

@route('/group/<gid>')
def groupSummary(gid):
    groupSummary = groups.getGroupSummary(gid)
    if groupSummary is not None:
        return template('base_page', renderpage="group", group=groupSummary, descriptionCache=descriptionCache)
    else:
        return redirect('/groups')

@route('/group/<gid>/ignore/<test>')
def ignoreTest(gid, test):
    groupSummary = groups.getGroupSummary(gid)
    groups.ignoreTest(gid, test)
    return redirect('/group/%s' % gid)

@route('/group/<gid>/include/<test>')
def includeTest(gid, test):
    groupSummary = groups.getGroupSummary(gid)
    groups.includeTest(gid, test)
    return redirect('/group/%s' % gid)

#FAILEDTEST-RELATED ROUTES
@route('/issues')
def issueSummary():
    issueSummary = issues.getIssueSummary()
    topIssues = issues.getTopIssues(5)
    return template('base_page', renderpage="issues", issueSummary=issueSummary, topIssues=topIssues, descriptionCache=descriptionCache)

#TICKET ROUTES
@route('/tickets')
@route('/tickets/<ticket>')
def ticketSummary(workflow=None, page=1):
    query = None
    if workflow != None:
        query = {"workflow":{"$in":[workflow]}}
    print query
    limit = 10
    if page == '':
        page = 1
    page = int(page)
    skip = (page - 1) * limit
    sortField = 'priority'
    order = pymongo.DESCENDING
    ticketSummary = tickets.getTicketSummary(query, sortField, order, skip, limit)
    return template('base_page', renderpage="tickets", ticketSummary=ticketSummary)

@route('/ticket/<ticket>/approve')
def approveTicket(ticket):
    tickets.approveTicket(ticket)
    return redirect('/tickets')

@route('/ticket/<ticket>/delay/<days>')
def delayTicket(ticket,days):
    tickets.delayTicket(ticket,days)
    return redirect('/tickets')

# STATIC FILES
@route('/js/<filename>')
def server_js(filename):
    return static_file(filename, root='./js')

@route('/css/<filename>')
def server_css(filename):
    return static_file(filename, root='./css')

@route('/img/<filename>')
def server_css(filename):
    return static_file(filename, root='./img')

connection_string = "mongodb://localhost"
connection = pymongo.MongoClient(connection_string)
database = connection.euphonia
karakuridb = connection.karakuri
groups = groupDAO.GroupDAO(database)
issues = issueDAO.IssueDAO(database)
tickets = ticketDAO.TicketDAO(karakuridb)

descriptionJSON = open('descriptions.json')
descriptionCache = json.load(descriptionJSON)
descriptionJSON.close()

run(reloader=True,host='0.0.0.0',port=8080)
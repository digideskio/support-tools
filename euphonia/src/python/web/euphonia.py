from bottle import route, run, template, static_file
import pymongo
import os
import failedTestDAO
import groupDAO

@route('/<page:re:\d*>')
def index(page=1):
    limit = 10
    if page == '':
        page = 1
    page = int(page)
    skip = (page - 1) * limit
    sortField = 'numFailedTests'
    order = pymongo.DESCENDING
    testsSummary = failedTests.getFailedTestsSummary(sortField=sortField,order=order,skip=skip,limit=limit)
    return template('base_page',renderpage="summary",groups=testsSummary['groups'],page=page,count=testsSummary['count'])

@route('/group/<gid>')
def groupSummary(gid):
    groupSummary = groups.getGroupSummary(gid)
    return template('base_page',renderpage="group",group=groupSummary)

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
failedTests = failedTestDAO.FailedTestDAO(database)
groups = groupDAO.GroupDAO(database)

run(host='localhost', port=8080)
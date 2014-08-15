from bottle import route, run, template, static_file, redirect
import pymongo
import os
import json
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
    return template('base_page',renderpage="group",group=groupSummary,descriptionCache=descriptionCache)

@route('/group/<gid>/ignore/<test>')
def ignoreTest(gid,test):
    groupSummary = groups.getGroupSummary(gid)
    groups.ignoreTest(gid,test)
    redirect('/group/%s' % gid)

@route('/group/<gid>/include/<test>')
def includeTest(gid,test):
    groupSummary = groups.getGroupSummary(gid)
    groups.includeTest(gid,test)
    redirect('/group/%s' % gid)

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
failedTests = failedTestDAO.FailedTestDAO(database)
groups = groupDAO.GroupDAO(database)

descriptionJSON = open('descriptions.json')
descriptionCache = json.load(descriptionJSON)
descriptionJSON.close()

run(port=8080)
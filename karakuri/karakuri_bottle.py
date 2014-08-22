import os
import pymongo
import sys

from bson.json_util import dumps
from bottle import route, run  # , template
from karakuri import karakuri
from ConfigParser import RawConfigParser

config = RawConfigParser()
config.read(os.getcwd() + "/karakuri.cfg")  # + options.config)

# Initialize MongoDB
# TODO configuration passed to MongoClient
mongodb = pymongo.MongoClient()
kk = karakuri(config, mongodb)


@route('/issue/<id>')
def get_issue(id):
    """ Return the given issue """
    issue = kk.getSupportIssue(id)

    if issue is not None:
        res = 0
    else:
        issue = {'doc': {}}
        res = 1

    return dumps({'res': res, 'data': issue.doc})


@route('/issue/<id>/sleep')
@route('/issue/<id>/sleep/<seconds:int>')
def issue_sleep(id, seconds=sys.maxint):
    """ Sleep the given issue. A sleeping issue cannot have queued actions """
    res = 0 if kk.sleepIssue(id, seconds) is not None else 1
    return dumps({'res': res})


@route('/issue/<id>/wake')
def issue_wake(id):
    """ Wake the given issue, i.e. unsleep it """
    res = 0 if kk.wakeIssue(id) is not None else 1
    return dumps({'res': res})


@route('/queue')
def lsqueue():
    """ Return the active queue by default """
    doc = kk.getListOfQueueDocuments()

    if doc is not None:
        res = 0
    else:
        doc = {}
        res = 1

    return dumps({'res': res, 'data': doc})


@route('/queue/<id>')
def queue(id):
    """ Return the queued action (document) """
    doc = kk.getQueueDocument(id)

    if doc is not None:
        res = 0
    else:
        doc = {}
        res = 1

    return dumps({'res': res, 'data': doc})


@route('/queue/<id>/approve')
def queue_approve(id):
    """ Approve the queued action. An approved action is one that will be
    performed """
    res = 0 if kk.approveQueue(id) is not None else 1
    return dumps({'res': res})


@route('/queue/<id>/remove')
def queue_remove(id):
    """ Remove the queued action """
    res = 0 if kk.sleepQueue(id, sys.maxint) is not None else 1
    return dumps({'res': res})


@route('/queue/<id>/sleep')
@route('/queue/<id>/sleep/<seconds:int>')
def queue_sleep(id, seconds=sys.maxint):
    """ Sleep the queued action. A sleeping action cannot be performed """
    res = 0 if kk.sleepQueue(id, seconds) is not None else 1
    return dumps({'res': res})


@route('/queue/<id>/wake')
def queue_wake(id):
    """ Wake the queued action, i.e. unsleep it """
    res = 0 if kk.wakeQueue(id) is not None else 1
    return dumps({'res': res})

@route('/workflow')
def lsworkflows():
    """ Return a list of workflow documents """
    doc = kk.getListOfWorkflowDocuments()

    if doc is not None:
        res = 0
    else:
        doc = {}
        res = 1

    return dumps({'res': res, 'data': doc})


@route('/workflow/<name>')
def get_workflow(name):
    """ Return the specified workflow document """
    doc = kk.getWorkflowDocument(name)

    if doc is not None:
        res = 0
    else:
        doc = {}
        res = 1

    return dumps({'res': res, 'data': doc})


run(host='localhost', port=8080)

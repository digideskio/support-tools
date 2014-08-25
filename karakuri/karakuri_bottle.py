import os
import sys

from bottle import route, run  # , template
from bson.json_util import dumps
from karakuri import karakuri
from ConfigParser import RawConfigParser


@route('/issue/<id>')
def get_issue(id):
    """ Return the given issue """
    issue = k.getSupportIssue(id)

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
    res = 0 if k.sleepIssue(id, seconds) is not None else 1
    return dumps({'res': res})


@route('/issue/<id>/wake')
def issue_wake(id):
    """ Wake the given issue, i.e. unsleep it """
    res = 0 if k.wakeIssue(id) is not None else 1
    return dumps({'res': res})


@route('/queue')
def lsqueue():
    """ Return the active queue by default """
    doc = k.getListOfQueueDocuments()

    if doc is not None:
        res = 0
    else:
        doc = {}
        res = 1

    return dumps({'res': res, 'data': doc})


@route('/queue/<id>')
def get_queue(id):
    """ Return the queued ticket """
    doc = k.getQueueDocument(id)

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
    res = 0 if k.approveQueue(id) is not None else 1
    return dumps({'res': res})


@route('/queue/<id>/disapprove')
def queue_disapprove(id):
    """ Disapprove the queued action. A disapproved action is one that will not
    be performed """
    res = 0 if k.approveQueue(id) is not None else 1
    return dumps({'res': res})


@route('/queue/<id>/remove')
def queue_remove(id):
    """ Remove the queued action """
    res = 0 if k.sleepQueue(id, sys.maxint) is not None else 1
    return dumps({'res': res})


@route('/queue/<id>/sleep')
@route('/queue/<id>/sleep/<seconds:int>')
def queue_sleep(id, seconds=sys.maxint):
    """ Sleep the queued action. A sleeping action cannot be performed """
    res = 0 if k.sleepQueue(id, seconds) is not None else 1
    return dumps({'res': res})


@route('/queue/<id>/wake')
def queue_wake(id):
    """ Wake the queued action, i.e. unsleep it """
    res = 0 if k.wakeQueue(id) is not None else 1
    return dumps({'res': res})


@route('/workflow')
def lsworkflows():
    """ Return a list of workflow documents """
    doc = k.getListOfWorkflowDocuments()

    if doc is not None:
        res = 0
    else:
        doc = {}
        res = 1

    return dumps({'res': res, 'data': doc})


@route('/workflow/<name>')
def get_workflow(name):
    """ Return the specified workflow document """
    doc = k.getWorkflowDocument(name)

    if doc is not None:
        res = 0
    else:
        doc = {}
        res = 1

    return dumps({'res': res, 'data': doc})

if __name__ == "__main__":
    config = RawConfigParser()
    config.read(os.getcwd() + "/karakuri.cfg")  # + options.config)
    k = karakuri(config)

    run(host='localhost', port=8080)

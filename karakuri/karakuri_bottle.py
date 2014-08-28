import bson.json_util
import os
import sys

from bottle import route, run  # , template
from karakuri import karakuri
from ConfigParser import RawConfigParser


@route('/issue')
def lsissue(id):
    """ Return a no-way, Jose 404 """
    # TODO implement no-way, Jose 404
    return bson.json_util.dumps({'res': 1, 'data': []})


@route('/issue/<id>')
def get_issue(id):
    """ Return the issue """
    issue = k.getSupportIssue(id)

    if issue is not None:
        res = 0
    else:
        issue = {'doc': {}}
        res = 1

    return bson.json_util.dumps({'res': res, 'data': issue.doc})


@route('/issue/<id>/sleep')
@route('/issue/<id>/sleep/<seconds:int>')
def issue_sleep(id, seconds=sys.maxint):
    """ Sleep the issue. A sleeping issue cannot have actions queued """
    res = 0 if k.sleepIssue(id, seconds) is not None else 1
    return bson.json_util.dumps({'res': res})


@route('/issue/<id>/wake')
def issue_wake(id):
    """ Wake the issue, i.e. unsleep it """
    res = 0 if k.wakeIssue(id) is not None else 1
    return bson.json_util.dumps({'res': res})


@route('/queue')
def lsqueue():
    """ Return a list of tickets """
    tickets = k.getListOfTickets()

    if tickets is not None:
        res = 0
    else:
        tickets = []
        res = 1

    return bson.json_util.dumps({'res': res, 'data': tickets})


@route('/queue/approve')
def queue_approve(id):
    """ Approve all active tickets, i.e. those that are not done """
    match = {'done': False}
    tickets = k.getListOfTicketIds(match)
    res = k.forListOfTickets(k.approveTicket, tickets)
    res = 0 if res else 1
    return bson.json_util.dumps({'res': res})


@route('/queue/disapprove')
def queue_disapprove(id):
    """ Disapprove all active tickets """
    match = {'done': False}
    tickets = k.getListOfTicketIds(match)
    res = k.forListOfTickets(k.disapproveTicket, tickets)
    res = 0 if res else 1
    return bson.json_util.dumps({'res': res})


@route('/queue/remove')
def queue_remove(id):
    """ Remove all active tickets """
    match = {'done': False}
    tickets = k.getListOfTicketIds(match)
    res = k.forListOfTickets(k.removeTicket, tickets)
    res = 0 if res else 1
    return bson.json_util.dumps({'res': res})


@route('/queue/sleep')
@route('/queue/sleep/<seconds:int>')
def queue_sleep(id, seconds=sys.maxint):
    match = {'done': False}
    """ Sleep all active tickets. A sleeping ticket cannot be acted upon """
    tickets = k.getListOfTicketIds(match)
    res = k.forListOfTickets(k.sleepTicket, tickets, seconds=seconds)
    res = 0 if res else 1
    return bson.json_util.dumps({'res': res})


@route('/queue/wake')
def queue_wake(id):
    """ Wake all active tickets """
    match = {'done': False}
    tickets = k.getListOfTicketIds(match)
    res = k.forListOfTickets(k.wakeTicket, tickets)
    res = 0 if res else 1
    return bson.json_util.dumps({'res': res})


@route('/ticket/<id>')
def get_ticket(id):
    """ Return the specified ticket """
    ticket = k.getTicket(id)

    if ticket is not None:
        res = 0
    else:
        ticket = {}
        res = 1

    return bson.json_util.dumps({'res': res, 'data': ticket})


@route('/ticket/<id>/approve')
def ticket_approve(id):
    """ Approve the ticket """
    res = 0 if k.approveTicket(id) is not None else 1
    return bson.json_util.dumps({'res': res})


@route('/ticket/<id>/disapprove')
def ticket_disapprove(id):
    """ Disapprove the ticket """
    res = 0 if k.disapproveTicket(id) is not None else 1
    return bson.json_util.dumps({'res': res})


@route('/ticket/<id>/remove')
def ticket_remove(id):
    """ Remove the ticket """
    res = 0 if k.removeTicket(id) is not None else 1
    return bson.json_util.dumps({'res': res})


@route('/ticket/<id>/sleep')
@route('/ticket/<id>/sleep/<seconds:int>')
def ticket_sleep(id, seconds=sys.maxint):
    """ Sleep the ticket. A sleeping ticket cannot be acted upon """
    res = 0 if k.sleepTicket(id, seconds) is not None else 1
    return bson.json_util.dumps({'res': res})


@route('/ticket/<id>/wake')
def ticket_wake(id):
    """ Wake the ticket, i.e. unsleep it """
    res = 0 if k.wakeTicket(id) is not None else 1
    return bson.json_util.dumps({'res': res})


@route('/workflow')
def lsworkflow():
    """ Return a list of workflows """
    workflows = k.getListOfWorkflows()

    if workflows is not None:
        res = 0
    else:
        workflows = {}
        res = 1

    return bson.json_util.dumps({'res': res, 'data': workflows})


@route('/workflow/<name>')
def get_workflow(name):
    """ Return the specified workflow """
    workflow = k.getWorkflow(name)

    if workflow is not None:
        res = 0
    else:
        workflow = {}
        res = 1

    return bson.json_util.dumps({'res': res, 'data': workflow})


@route('/workflow/<name>/approve')
def workflow_approve(name):
    """ Approve all active tickets in the workflow """
    match = {'workflow': name, 'done': False}
    tickets = k.getListOfTicketIds(match)
    print(tickets)
    res = k.forListOfTickets(k.approveTicket, tickets)
    res = 0 if res else 1
    return bson.json_util.dumps({'res': res})


@route('/workflow/<name>/disapprove')
def workflow_disapprove(name):
    """ Disapprove all active tickets in the workflow """
    match = {'workflow': name, 'done': False}
    tickets = k.getListOfTicketIds(match)
    res = k.forListOfTickets(k.disapproveTicket, tickets)
    res = 0 if res else 1
    return bson.json_util.dumps({'res': res})


@route('/workflow/<name>/remove')
def workflow_remove(name):
    """ Remove all active tickets in the workflow """
    match = {'workflow': name, 'done': False}
    tickets = k.getListOfTicketIds(match)
    res = k.forListOfTickets(k.removeTicket, tickets)
    res = 0 if res else 1
    return bson.json_util.dumps({'res': res})


@route('/workflow/<name>/sleep')
@route('/workflow/<name>/sleep/<seconds:int>')
def workflow_sleep(name, seconds=sys.maxint):
    """ Sleep all active tickets in the workflow """
    match = {'workflow': name, 'done': False}
    tickets = k.getListOfTicketIds(match)
    res = k.forListOfTickets(k.sleepTicket, tickets, seconds=seconds)
    res = 0 if res else 1
    return bson.json_util.dumps({'res': res})


@route('/workflow/<name>/wake')
def workflow_wake(name):
    """ Wake all active tickets in the workflow """
    match = {'workflow': name, 'done': False}
    tickets = k.getListOfTicketIds(match)
    res = k.forListOfTickets(k.wakeTicket, tickets)
    res = 0 if res else 1
    return bson.json_util.dumps({'res': res})

if __name__ == "__main__":
    configFilename = os.getcwd() + "/karakuri.cfg"
    logFilename = os.getcwd() + "/karakuri_bottle.cfg"
    config = RawConfigParser()
    config.read(configFilename)  # + options.config)
    if not config.has_section("CLI"):
        config.add_section("CLI")
    config.set("CLI", "config", configFilename)
    config.set("CLI", "log", logFilename)
    k = karakuri(config)

    run(host='localhost', port=8080)

import bson.json_util
import os

from bottle import post, request, route, run, static_file, template
from karakuri import karakuri

#
# Services for editing workflows
#


@route('/')
def index():
    workflows = k.getListOfWorkflows()
    return template('base_page', renderpage="workflows", workflows=workflows)


@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='./static')


@post('/editworkflow')
def edit_workflow():
    formcontent = request.body.read()
    formjson = bson.json_util.loads(formcontent)
    print formjson
    for workflow in formjson.get('workflow'):
        workflowId = bson.json_util.ObjectId(workflow.get('_id'))
        workflow['_id'] = workflowId
        print workflow
        k.mongo.karakuri.workflows.update({'_id': workflowId}, workflow)

if __name__ == "__main__":
    configFilename = os.getcwd() + "/karakuri.cfg"
    logFilename = os.getcwd() + "/karakuri_bottle.cfg"
    args = {'config': configFilename, 'log': logFilename}
    k = karakuri(args)

    run(host='localhost', port=8080)

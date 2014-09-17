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
    return template('workflows', workflows=workflows)


@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='/Users/jribnik/devel/github/'
                                      '10gen-support-tools/karakuri/static')


@post('/editworkflow')
def edit_workflow():
    _id = request.params.get('_id')
    if not isinstance(_id, bson.ObjectId):
        _id = bson.ObjectId(_id)
    field = request.params.get('field')
    val = request.params.get('val')
    k.mongo.karakuri.workflows.update({'_id': _id}, {"$set": {field: val}})

if __name__ == "__main__":
    configFilename = os.getcwd() + "/karakuri.cfg"
    logFilename = os.getcwd() + "/karakuri_bottle.cfg"
    args = {'config': configFilename, 'log': logFilename}
    k = karakuri(args)

    run(host='localhost', port=8080)

import requests
from bson.json_util import loads

class karakuriDAO:

    def __init__(self, server):
        self.SERVER = server

    def executeKarakuriCall(self, url):
        try:
            r = requests.get(url)
            response = loads(r.text)
            if 'data' in response:
                return response['data']

        except:
            print "Failed to call: " + url

    # QUEUE FUNCTIONS
    def getQueues(self):
        getUrl = "%s/queue" % (self.SERVER)
        response = self.executeKarakuriCall(getUrl)
        return response

    def getQueue(self, queueId):
        getUrl = "%s/queue/%s" % (self.SERVER, queueId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def approveQueue(self, queueId):
        getUrl = "%s/queue/%s/approve" % (self.SERVER, queueId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def disapproveQueue(self, queueId):
        getUrl = "%s/queue/%s/disapprove" % (self.SERVER, queueId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def removeQueue(self, queueId):
        getUrl = "%s/queue/%s/remove" % (self.SERVER, queueId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def sleepQueue(self, queueId, seconds=86400):
        getUrl = "%s/queue/%s/sleep/%s" % (self.SERVER, queueId, seconds)
        response = self.executeKarakuriCall(getUrl)
        return response

    def wakeQueue(self, queueId):
        getUrl = "%s/queue/%s/wake" % (self.SERVER, queueId)
        response = self.executeKarakuriCall(getUrl)
        return response

    # WORKFLOW FUNCTIONS
    def getWorkflows(self):
        getUrl = "%s/workflow" % (self.SERVER)
        response = self.executeKarakuriCall(getUrl)
        return response

    def getWorkflow(self, workflowId):
        getUrl = "%s/workflow/%s" % (self.SERVER, workflowId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def approveWorkflow(self, workflowId):
        getUrl = "%s/workflow/%s/approve" % (self.SERVER, workflowId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def disapproveWorkflow(self, workflowId):
        getUrl = "%s/workflow/%s/disapprove" % (self.SERVER, workflowId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def removeWorkflow(self, workflowId):
        getUrl = "%s/workflow/%s/remove" % (self.SERVER, workflowId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def sleepWorkflow(self, workflowId, seconds=86400):
        getUrl = "%s/workflow/%s/sleep/%s" % (self.SERVER, workflowId, seconds)
        response = self.executeKarakuriCall(getUrl)
        return response

    def wakeWorkflow(self, workflowId):
        getUrl = "%s/workflow/%s/wake" % (self.SERVER, workflowId)
        response = self.executeKarakuriCall(getUrl)
        return response

    # TICKET FUNCTIONS
    def getTicket(self, ticketId):
        getUrl = "%s/ticket/%s" % (self.SERVER, ticketId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def approveTicket(self, ticketId):
        getUrl = "%s/ticket/%s/approve" % (self.SERVER, ticketId)
        response = self.executeKarakuriCall(getUrl)
        print getUrl
        print response
        return response

    def disapproveTicket(self, ticketId):
        getUrl = "%s/ticket/%s/approve" % (self.SERVER, ticketId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def removeTicket(self, ticketId):
        getUrl = "%s/ticket/%s/remove" % (self.SERVER, ticketId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def sleepTicket(self, ticketId, seconds=86400):
        getUrl = "%s/ticket/%s/sleep/%s" % (self.SERVER, ticketId, seconds)
        response = self.executeKarakuriCall(getUrl)
        return response

    def wakeTicket(self, ticketId):
        getUrl = "%s/issue/%s/wake" % (self.SERVER, ticketId)
        response = self.executeKarakuriCall(getUrl)
        return response

    # ISSUE FUNCTIONS
    def getIssue(self, issueId):
        getUrl = "%s/issue/%s" % (self.SERVER, issueId)
        response = self.executeKarakuriCall(getUrl)
        return response

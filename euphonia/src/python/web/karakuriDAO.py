import requests

class karakuriDAO:

    def __init__(self, server):
        self.SERVER = server

    def executeKarakuriCall(self, url):
        try:
            r = requests.get(url)
            print r
            return r
        except:
            print "Failed to call: " + url

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

    def getTicket(self, ticketId):
        getUrl = "%s/issue/%s" % (self.SERVER, ticketId)
        response = self.executeKarakuriCall(getUrl)
        return response

    def sleepTicket(self, ticketId, seconds=86400):
        getUrl = "%s/issue/%s/sleep/%s" % (self.SERVER, ticketId, seconds)
        response = self.executeKarakuriCall(getUrl)
        return response

    def wakeTicket(self, ticketId):
        getUrl = "%s/issue/%s/wake" % (self.SERVER, ticketId)
        response = self.executeKarakuriCall(getUrl)
        return response
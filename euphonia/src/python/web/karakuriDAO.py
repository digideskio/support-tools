import requests

class karakuriDAO:

    def __init__(self, server):
        self.SERVER = server

    def approveTicket(self, ticketId):
        getUrl = "%s/approve/%s" % (self.SERVER, ticketId)
        print getUrl
        #r = requests.get(getUrl)
        #print r

    def delayTicket(self, ticketId, days=1):
        getUrl = "%s/approve/%s/%s" % (self.SERVER, ticketId, days)
        print getUrl
        #r = requests.get(getUrl)
        #print r
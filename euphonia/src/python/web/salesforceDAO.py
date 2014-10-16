import requests
from simple_salesforce import Salesforce
from bson import json_util

class salesforceDAO:

    def __init__(self):
        self.server = "https://mongodb.my.salesforce.com"
        self.session = "00DA0000000Kz0l!AQgAQD1i1yKkEcQxZDvb4xxrfvnoIn481dgsR1cmvy4Pd5UtURU_nqubueRtdpq8zYD1_..9BLRocjlMO2tuslW6Txf86Cyk"
        self.connection = Salesforce(instance_url=self.server, session_id=self.session, version="32.0")

    # QUEUE FUNCTIONS
    def getContacts(self):
        result = self.connection.Project__c.get('a0OA000000969i0MAA')
        for item in result:
            print "%s : %s" % (item, result[item])

    def getQueue(self, queueId):
        getUrl = "%s/queue/%s" % (self.server, queueId)
        response = self.executeKarakuriCall(getUrl)
        return response

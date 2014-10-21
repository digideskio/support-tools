import pyforce


class Salesforce:

    def __init__(self):
        self.server = "https://mongodb.my.salesforce.com"
        self.session = "00DA0000000Kz0"
        self.connection = pyforce.PythonClient(serverUrl=self.server)

    # QUEUE FUNCTIONS
    def getcontacts(self):
        result = None
        for item in result:
            print "%s : %s" % (item, result[item])

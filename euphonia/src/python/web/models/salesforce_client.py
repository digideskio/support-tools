import pyforce


class Salesforce:

    def __init__(self):
        self.server = "https://mongodb.my.salesforce.com"
        self.session = "00DA0000000Kz0"
        self.connection = pyforce.PythonClient()
        l = "paul.rooney@mongodb.com"
        p = "Aequitas2852^sJB7qLmqKcuXGWLSmkAwTUGA"
        self.connection.login(l, p)

    # QUEUE FUNCTIONS
    def get_contacts(self):
        print self.connection.isConnected()

    def get_sf_project_onboard_status(self):
        soql = "SELECT Account_Name_text__c,Account__c,Clienthub_ID__c,Id,Name FROM Project__c ORDER BY Name"
        results = self.connection.query(soql)
        while not results.done:
            for result in results:
                print result['Name']
            results = self.connection.queryMore(self.connection.queryLocator)

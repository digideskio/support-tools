import pyforce


class Salesforce:
    """ This class manages the Salesforce connection and queries
    """

    def __init__(self):
        """ Initializes Tests class with a database object.
        :return: None
        """
        self.server = "https://mongodb.my.salesforce.com"
        self.session = "00DA0000000Kz0"
        self.connection = pyforce.PythonClient()
        l = "sfdctest@mongodb.com"
        p = "SjdnWjkiej38hhkOj28JB7qLmqHFJDksje38e"
        self.connection.login(l, p)

    def get_contacts(self):
        """ INCOMPLETE FUNCTION
        :return: Boolean
        """
        return self.connection.isConnected()

    def get_sf_project_onboard_status(self):
        """ INCOMPLETE FUNCTION
        :return: Boolean
        """
        soql = "SELECT Account_Name_text__c,Account__c,Clienthub_ID__c,Id,Name FROM Project__c ORDER BY Name"
        results = self.connection.query(soql)
        while not results.done:
            for result in results:
                print result['Name']
            results = self.connection.queryMore(self.connection.queryLocator)
        return True

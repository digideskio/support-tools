import pymongo

class IssueDAO:

    def __init__(self,database):
        self.group_collection = database.groupsummaries
        self.issue_collection = database.failedtests

    def getIssueSummary(self):
        priorities = ['low','medium','high']
        pCount = {}
        total = 0
        for priority in priorities:
            results = self.issue_collection.find({"priority":priority}).count()
            total = total + results
            pCount[priority] = results
        pCount['total'] = total
        return pCount

    def getTopIssues(self,limit):
        results = self.issue_collection.aggregate([{"$group":{"_id":"$test","failedCount":{"$sum":1}}},{"$sort":{"failedCount":-1}}])
        return results['result']

    def ignoreTest(self,gid,test):
        self.issue_collection.update({"GroupId":gid,"failedTests.test":test},{"$set":{"failedTests.$.ignore":1}})

    def includeTest(self,gid,test):
        self.issue_collection.update({"GroupId":gid,"failedTests.test":test},{"$set":{"failedTests.$.ignore":0}})
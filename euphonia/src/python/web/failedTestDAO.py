from collections import OrderedDict
import pymongo
import bson

class FailedTestDAO:

    def __init__(self,database):
        self.group_collection = database.groupsummaries
        self.issue_collection = database.failedtests

    def getFailedTestsSummary(self):
        priorities = ['low','medium','high']
        pCount = {}
        total = 0
        for priority in priorities:
            results = self.issue_collection.find({"priority":priority}).count()
            total = total + results
            pCount[priority] = results
        pCount['total'] = total
        return pCount

    def getTopFailedTests(self,limit):
        results = self.issue_collection.aggregate([{"$group":{"_id":"$test","failedCount":{"$sum":1}}},{"$sort":{"failedCount":-1}}])
        return results['result']

    def ignoreTest(self,gid,test):
        self.issue_collection.update({"GroupId":gid,"failedTests.test":test},{"$set":{"failedTests.$.ignore":1}})

    def includeTest(self,gid,test):
        self.issue_collection.update({"GroupId":gid,"failedTests.test":test},{"$set":{"failedTests.$.ignore":0}})
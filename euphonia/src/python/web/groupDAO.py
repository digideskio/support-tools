import pymongo

class GroupDAO:

    def __init__(self,database):
        self.collection = database.groupsummaries


    def getGroupSummary(self,gid):
        results = self.collection.find({"GroupId":gid}).sort("testTimestamp",pymongo.DESCENDING).limit(1)
        groupSummary = next(results,None)
        # dataPoints = []
        # while groupDataPoint != None:
        #    dataPoints.append(groupDataPoint)
        #    groupDataPoint = next(results,None)
        #return dataPoints
        return groupSummary

    def ignoreTest(self,gid,test):
        self.collection.update({"GroupId":gid,"failedTests.test":test},{"$set":{"failedTests.$.ignore":1}})

    def includeTest(self,gid,test):
        self.collection.update({"GroupId":gid,"failedTests.test":test},{"$set":{"failedTests.$.ignore":0}})
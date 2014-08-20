import pymongo
import bson

class GroupDAO:

    def __init__(self,database):
        self.collection = database.groupsummaries


    def getGroupSummary(self,gid):
        results = self.collection.find({"GroupId":gid}).sort("priority",pymongo.DESCENDING).limit(1)
        groupSummary = next(results,None)
        # dataPoints = []
        # while groupDataPoint != None:
        #    dataPoints.append(groupDataPoint)
        #    groupDataPoint = next(results,None)
        #return dataPoints
        return groupSummary

    def getFailedTestsSummary(self,sortField,order=pymongo.ASCENDING,skip=0,limit=10,query=None):
        fquery = {}
        if query != None:
            fquery = query
        results = self.collection.find(fquery,as_class=bson.son.SON).sort(sortField, order).skip(skip).limit(limit)
        groupCount = results.count()
        groups = []
        group = next(results,None)
        while group != None:
            groups.append(group)
            group = next(results,None)
        return {"groups":groups,"count":groupCount}

    def getGroupsWithFailedTest(self,test,limit=100):
        results = self.collection.find({"failedTests.test":{"$in":[test]}}).sort({"priority":pymongo.DESCENDING}).limit(limit)

    def ignoreTest(self,gid,test):
        self.collection.update({"GroupId":gid,"failedTests.test":test},{"$set":{"failedTests.$.ignore":1}})

    def includeTest(self,gid,test):
        self.collection.update({"GroupId":gid,"failedTests.test":test},{"$set":{"failedTests.$.ignore":0}})
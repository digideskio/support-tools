import pymongo
import bson


class Groups:

    def __init__(self, database):
        self.collection = database.groupsummaries

    def getGroupSummary(self, gid):
        query = {"GroupId": gid}
        results = self.collection.find(query)\
                      .sort("priority", pymongo.DESCENDING)\
                      .limit(1)
        groupSummary = next(results, None)
        return groupSummary

    def getFailedTestsSummary(self, sortField,
                              order=pymongo.ASCENDING, skip=0,
                              limit=10, query=None):
        fquery = {}
        if query is not None:
            fquery = query
        results = self.collection.find(fquery, as_class=bson.son.SON)\
                      .sort(sortField, order)\
                      .skip(skip)\
                      .limit(limit)
        groupCount = results.count()
        groups = []
        group = next(results, None)
        while group is not None:
            groups.append(group)
            group = next(results, None)
        return {"groups": groups, "count": groupCount}

    def ignoreTest(self, gid, test):
        match = {"GroupId": gid, "failedTests.test": test}
        update = {"$set": {"failedTests.$.ignore": 1}}
        self.collection.update(match, update)

    def includeTest(self, gid, test):
        match = {"GroupId": gid, "failedTests.test": test}
        update = {"$set": {"failedTests.$.ignore": 0}}
        self.collection.update(match, update)

    def search(self, query):
        qregex = "^%s" % query
        query = {"GroupName": {"$regex": qregex, "$options": "i"}}
        project = {"GroupName": 1, "GroupId": 1, "_id": 0}
        results = self.collection.find(query, project)\
                      .sort("GroupName", 1)\
                      .limit(10)
        groups = []
        group = next(results, None)
        while group is not None:
            groups.append(group)
            group = next(results, None)
        return groups

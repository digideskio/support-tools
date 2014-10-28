import pymongo


class Groups:

    def __init__(self, database):
        self.collection = database.groupsummaries

    def get_group_summary(self, gid):
        query = {"GroupId": gid}
        results = self.collection.find(query)\
                      .sort("priority", pymongo.DESCENDING)\
                      .limit(1)
        group_summary = next(results, None)
        return group_summary

    def get_failed_tests_summary(self, sort=[("priority", pymongo.DESCENDING)],
                                 skip=0, limit=10, query=None):
        fquery = {}
        if query is not None:
            fquery = query
        results = self.collection.find(fquery)\
                      .sort(sort)\
                      .skip(skip)\
                      .limit(limit)
        group_count = results.count()
        groups = []
        group = next(results, None)
        while group is not None:
            groups.append(group)
            group = next(results, None)
        return {"groups": groups, "count": group_count}

    def ignore_test(self, gid, test):
        match = {"GroupId": gid, "failedTests.test": test}
        update = {"$set": {"failedTests.$.ignore": 1}}
        self.collection.update(match, update)

    def include_test(self, gid, test):
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

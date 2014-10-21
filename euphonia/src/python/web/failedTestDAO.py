class FailedTests:

    def __init__(self, database):
        self.group_collection = database.groupsummaries
        self.issue_collection = database.failedtests

    def getFailedTestsSummary(self):
        priorities = ['low', 'medium', 'high']
        pCount = {}
        total = 0
        for priority in priorities:
            search = {"priority": priority}
            results = self.issue_collection.find(search).count()
            total = total + results
            pCount[priority] = results
        pCount['total'] = total
        return pCount

    def getTopFailedTests(self, limit):
        limit = {"$limit": limit}
        sort = {"$sort": {"failedCount": -1}}
        group = {"$group": {"_id": "$test", "failedCount": {"$sum": 1}}}
        results = self.issue_collection.aggregate([group, sort, limit])
        return results['result']

    def ignoreTest(self, gid, test):
        match = {"GroupId": gid, "failedTests.test": test}
        update = {"$set": {"failedTests.$.ignore": 1}}
        self.issue_collection.update(match, update)

    def includeTest(self, gid, test):
        match = {"GroupId": gid, "failedTests.test": test}
        update = {"$set": {"failedTests.$.ignore": 0}}
        self.issue_collection.update(match, update)

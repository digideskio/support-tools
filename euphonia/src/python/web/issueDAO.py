import pymongo
import bson
from bson.objectid import ObjectId
from datetime import datetime, timedelta

class IssueDAO:

    def __init__(self, database):
        self.collection = database.issues

    def getIssueSummaries(self, issueIds):
        print issueIds
        results = self.collection.find({"_id": {"$in": issueIds}}, {"jira.key": 1, "jira.self": 1})
        issues = {}
        issue = next(results, None)
        while issue is not None:
            issues[str(issue['_id'])] = issue['jira']
            issue = next(results, None)
        print issues
        return issues
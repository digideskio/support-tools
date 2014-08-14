from collections import OrderedDict
import pymongo
import bson

class FailedTestDAO:

    def __init__(self,database):
        self.collection = database.groupsummaries


    def getFailedTestsSummary(self,sortField,order=pymongo.ASCENDING,skip=0,limit=10):
        results = self.collection.find({},as_class=bson.son.SON).sort(sortField, order).skip(skip).limit(limit)
        groupCount = results.count()
        groups = []
        group = next(results,None)
        while group != None:
            groups.append(group)
            group = next(results,None)
        return {"groups":groups,"count":groupCount}
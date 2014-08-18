from collections import OrderedDict
import pymongo
import bson

class FailedTestDAO:

    def __init__(self,database):
        self.collection = database.groupsummaries



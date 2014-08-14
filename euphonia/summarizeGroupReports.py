import pymongo
import sys

conn = pymongo.MongoClient()
db = conn.euphonia
coll_mmsgroupreports = db.mmsgroupreports
coll_failedtests = db.failedtests

groups = coll_mmsgroupreports.find({})
for group in groups:

coll_failedtests.aggregate(pipeline)
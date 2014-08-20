import pymongo
import sys

# from bson.son import SON
# from pprint import pprint
from groupreport import GroupReport


conn = pymongo.MongoClient()
db = conn.euphonia
coll_mmsgroupreports = db.mmsgroupreports
coll_failedtests = db.failedtests
coll_groupsummaries = db.groupsummaries

# If tag not specified get the latest entry by _id
# and analyze groups with common tag
tag = coll_mmsgroupreports.find({}, {"_id": 0, "tag": 1}).sort("_id", -1).\
    limit(1)[0]['tag']
find = {"tag": tag}

# There are much fewer fails than passes, so cache
# unprocessed fails up front for faster processing
match = {'ticket': {"$exists": 0}}
proj = {'gid': 1, 'test': 1}
curs_tests = coll_failedtests.find(match, proj)
fails = {}
for t in curs_tests:
    if t['gid'] not in fails:
        fails[t['gid']] = {}
    # assert there is only one
    if t['test'] in fails[t['gid']]:
        print "Error: >1 %s for $s" % (t['test'], t['gid'])
        sys.exit(1)
    fails[t['gid']][t['test']] = t['_id']

try:
    curs_groups = coll_mmsgroupreports.find(find)
except Exception as e:
    raise e

for group in curs_groups:
    # CS customers only for now. I can imagine using Proactive Support to sell
    # subscriptions in the first place. If that ever happens we'll give the CS
    # customers more weight in the results.
    if group['IsCsCustomer'] is not True:
        continue

    g = GroupReport(group)
    results = g.runAllTests()

    failedTests = []
    for r in results:
        # If a passing test had previously failed but has not yet been acted
        # upon, remove it from the list of failures
        if results[r] is True:
            if group['GroupId'] in fails:
                if r in fails[group['GroupId']]:
                    _id = fails[group['GroupId']][r]
                    print "Fail -> Pass! Removing %s from failedtests" % (_id)
                    coll_failedtests.remove({'_id': _id})
            continue

        # Persist failures
        failedTests.append({"test":r,"ignore":0,"notified":0,"priority": g.tests[r],"priorityScore":g.testPriorityScores[g.tests[r]]})
        match =  {'gid': group['GroupId'], 'test': r, 'ticket': {"$exists": 0}}
        updoc =  {"$addToSet": {'rids': group['_id']},
                  "$setOnInsert": {'gid': group['GroupId'], 'test': r, 'priority': g.tests[r],
                                  'name': group['GroupName']}}
        coll_failedtests.update(match, updoc, upsert=True)


    # Build summary document containing customer info and failed tests
    group['numFailedTests'] = len(failedTests)
    group['failedTests'] = failedTests
    failedTestsPriority = 0.0
    for test in failedTests:
        failedTestsPriority += float(test['priorityScore'])
    group['priority'] = failedTestsPriority
    group['testTimestamp'] = group['_id'].generation_time
    coll_groupsummaries.insert(group)
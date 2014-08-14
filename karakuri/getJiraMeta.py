import os
import pymongo

from jira.client import JIRA
from ConfigParser import RawConfigParser


conn = pymongo.MongoClient()
db = conn.jirameta
coll_transitions = db.transitions
coll_createmeta = db.createmeta

config = RawConfigParser()
config.read(os.getcwd() + '/jira.cfg')

opts = {'server': 'https://jira.mongodb.org', "verify": False}
auth = (config.get('JIRA', 'username'), config.get('JIRA', 'password'))
jira = JIRA(options=opts, basic_auth=auth)

projects = jira.projects()
statuses = jira.statuses()

#
# createmeta
#

for p in projects:
    print "Get createmeta for %s project..." % p
    try:
        createmeta = jira.createmeta(projectKeys=p,
                                     expand="projects.issuetypes.fields")

    except:
        print "Failed to get createmeta for %s project!" % p
        continue

    if 'projects' not in createmeta or len(createmeta['projects']) == 0:
        print "%s project not in createmeta, skipping" % p
        continue

    # 0 guaranteed because we used single project
    if 'issuetypes' not in createmeta['projects'][0]:
        print "%s project has no issuetypes, skipping" % p
        continue

    issuetypes = createmeta['projects'][0]['issuetypes']

    for issuetype in issuetypes:
        _id = "%s_%s" % (p.id, issuetype['id'])
        doc = {'_id': _id, 'pid': p.id, 'pkey': p.key,
               'itid': issuetype['id'], 'itname': issuetype['name'],
               'required': []}
        fields = issuetype['fields']

        for f in fields:
            if fields[f]['required'] is True:
                doc['required'].append(f)

    print "Write to MongoDB..."
    try:
        coll_createmeta.save(doc)
    except:
        print "Failed to write to MongoDB!"

#
# transitions
#

# This all assumes that transitions are unique to projects
# and statuses, and independent of issue type.
for p in projects:
    for s in statuses:
        search = "project='%s' AND status='%s'" % (p, s)

        print "Search for %s %s issue..." % (p, s)
        try:
            issues = jira.search_issues(search, maxResults=1)
        except:
            print "Failed to search for %s %s issue!" % (p, s)
            continue

        if len(issues) == 1:
            issue = issues[0]

            print "Get transitions for %s..." % issue.key
            try:
                transitions = jira.transitions(issue)
            except:
                print "Failed to get transitions for %s!" % issue.key
                continue

            for t in transitions:
                _id = "%s_%s_%s" % (p.id, s.id, t['id'])
                doc = {'_id': _id, 'pid': p.id, 'pkey': p.key, 'sid': s.id,
                       'sname': s.name, 'tid': t['id'], 'tname': t['name']}

                print "Write to MongoDB..."
                try:
                    coll_transitions.save(doc)
                except:
                    print "Failed to write to MongoDB!"
                    continue

        else:
            print "No %s %s tickets found" % (s, p)

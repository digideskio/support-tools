import json
import os
import pymongo

from bson.objectid import ObjectId
from datetime import datetime, timedelta
from jirapp import jirapp
from supportissue import isMongoDBEmail, SupportIssue
from ConfigParser import RawConfigParser


class Karakuri:
    def __init__(self, config, mongodb):
        self.ticketer = None
        self.live = False

        # Initialize databases and collections
        self.db_jirameta = mongodb.jirameta
        self.db_support = mongodb.support
        self.db_karakuri = mongodb.karakuri
        self.coll_issues = self.db_support.issues
        self.coll_workflows = self.db_karakuri.workflows
        self.coll_logs = self.db_karakuri.logs

        # TODO extract JIRA specific config and pass to JIRA++
        # Initialize JIRA++
        self.jirapp = jirapp(config, self.db_jirameta, self.db_support)
        self.jirapp.setLive(self.live)

        # Set the ticketer. Currently there is only one :(
        self.setTicketer(self.jirapp)

    def setTicketer(self, ticketer):
        self.ticketer = ticketer

    def run(self):
        # process each workflow
        try:
            curs_workflows = self.coll_workflows.find()
        except pymongo.errors.PyMongoError as e:
            raise e

        for workflow in curs_workflows:
            print "Exercising %s workflow..." % workflow['name']

            query_string = workflow['query_string']
            match = json.loads(query_string)

            # do not include issues for which the given workflow
            # has already been performed!
            if "$and" not in match:
                match["$and"] = []
            match["$and"].append({'karakuri.workflows_performed.name': {"$ne":
                                  workflow['name']}})

            if 'prereqs' in workflow:
                # require each prerequisite is met
                prereqs = workflow['prereqs']
                print "Considering prereqs: %s" % ', '.join(map(str, prereqs))
                for prereq in prereqs:
                    match['$and'].append({'karakuri.workflows_performed.name':
                                          prereq})

            # find 'em and get 'er done!
            try:
                curs_issues = self.coll_issues.find(match)
            except pymongo.errors.PyMongoError as e:
                raise e

            for i in curs_issues:
                # JIRA is the only option for now
                if 'jira' in i:
                    issue = SupportIssue()
                    issue.fromJIRADoc(i)
                else:
                    print "Skipping unsupported ticketing type!"
                    continue

                # is the onus on them?
                # if issue.status != "Waiting for Customer":
                #    continue

                # require time_elapsed has passed since last public comment
                # use 'updated' as comment could have been created dev-only
                # lastPublicComment = issue.lastXGenPublicComment

                # NOTE to compare with karakuri.rb, require that the user has
                # never before commented, and that the issue either does not
                # have a company (customfield_10030), does not have a MongoDB
                # assignee, or does not have a MongoDB reporter; i.e. the ruby
                # is innocent until proven guilty
                rubypass = True

                # if no public comments, use issue updated
                # if lastPublicComment is None:
                lastDate = issue.updated
                # else:
                #    lastDate = lastPublicComment['updated']

                # it's possible that we got here after a previous workflow
                # and before our jira was updated to reflect that
                if 'karakuri' in i:
                    if 'updated' in i['karakuri']:
                        lastKarakuri = i['karakuri']['updated']
                        if lastKarakuri > lastDate:
                            lastDate = lastKarakuri

                #
                # ruby simulation
                #
                company = issue.company
                assigneeEmail = issue.assigneeEmail

                assigneeIsMongoDB = isMongoDBEmail(assigneeEmail)
                reporterEmail = issue.reporterEmail
                reporterIsMongoDB = isMongoDBEmail(reporterEmail)

                if rubypass:
                    if company is not None or assigneeIsMongoDB is False or\
                            reporterIsMongoDB is False:
                        pass
                    else:
                        rubypass = False

                # has enough time elapsed?
                time_elapsed = timedelta(seconds=workflow['time_elapsed'])
                # in UTC please!
                now = datetime.utcnow()

                if lastDate + time_elapsed < now and rubypass:
                    print "%s, come on down! You're the next con-ticket on "\
                          "the Support-is-right!" % issue.key

                    # success of the entire workflow
                    # so far so good
                    success = True

                    actions = workflow['actions']
                    for action in actions:
                        # Is this a real action?
                        if hasattr(self.ticketer, action['name']):
                            args = []

                            if 'args' in action:
                                args = list(action['args'])
                            else:
                                args = []

                            # first argument is the ticket "id", i.e. that
                            # which the specific ticketing system will use
                            args.insert(0, issue.ticketId)
                            # for the sake of logging reduce string arguments
                            # to 50 characters and replace \n with \\n
                            argString = (', '.join('"' + arg[:50].replace('\n',
                                         '\\n') + '"' for arg in args))
                            print "Executing: %s(%s)" % (action['name'],
                                                         argString)

                            if self.live:
                                f = getattr(self.ticketer, action['name'])
                                # expand list to function arguments
                                r = f(*args)

                                if not r:
                                    # if one fails the whole workflow fails
                                    success = False
                                    break

                        else:
                            raise Exception("Error: %s is not a supported\
                                    action" % action['name'])

                    if success and self.live:
                        # we'll log this workflow in two places
                        # 1. karakuri.logs
                        # 2. support.issues.karakuri
                        # with a common object id for timing
                        _id = ObjectId()
                        logdoc = {'_id': _id, 'id': issue.id, 'workflow':
                                  workflow['name']}
                        self.coll_logs.insert(logdoc)

                        match = {'_id': issue.id}
                        updoc = {'$set': {'karakuri.updated':
                                 datetime.utcnow()},
                                 '$push':
                                 {'karakuri.workflows_performed':
                                  {'name': workflow['name'], 'log': _id}}}

                        try:
                            self.coll_issues.update(match, updoc)
                        except pymongo.errors.PyMongoError as e:
                            raise e

#
# Parse command line options
#

#
# Parse configuration file
#

config = RawConfigParser()
config.read(os.getcwd() + "/karakuri.cfg")  # + options.config)

# Initialize MongoDB
# TODO configuration passed to MongoClient
mongodb = pymongo.MongoClient()

kk = Karakuri(config, mongodb)
kk.run()

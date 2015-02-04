import argparse
import logging
import pymongo
import sys


class TestFramework:
    """ I dare say this class needs a better description than this! """
    def __init__(self, args):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args
        self.src = self.args['src']
        # this is where we save failed test names and the corresponding failed
        # test document _ids in euphonia.groups documents
        self.failedTestsPath = 'failedTests'

        # logLevel = self.args['log_level']
        logLevel = "DEBUG"
        logging.basicConfig()
        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logLevel)

        self.mongo = pymongo.MongoClient(host=args["mongo_host"], port=args["mongo_port"])
        self.db = self.mongo.euphonia
        self.coll_failedtests = self.db.failedtests
        self.coll_groups = self.db.groups

        if self.src == 'mdiags':
            self.logger.info("Testing mdiags...")
            # from mdiag import Mdiag as TestDocumentClass
            # self.coll_src = self.db.mdiags
        elif self.src == 'mmsgroupreports':
            self.logger.info("Testing mmsgroupreports...")
            from groupreport import GroupReport as TestDocumentClass
            self.coll_src = self.db.mmsgroupreports
            self.groupIdKey = 'GroupId'
            self.groupIdQuery = {}
        elif self.src == 'pings':
            self.logger.info("Testing pings...")
            from groupping import GroupPing as TestDocumentClass
            self.coll_src = self.db.pings
            self.groupIdKey = 'gid'
            self.groupIdQuery = {}
        else:
            self.logger.exception("%s is not a supported src", self.src)
            sys.exit(1)

        self.testDocumentClass = TestDocumentClass

    def testAllGroups(self):
        self.logger.debug("testAllGroups()")
        try:
            groupIds = self.coll_src.find(self.groupIdQuery).\
                distinct(self.groupIdKey)
        except pymongo.errors.PyMongoError as e:
            raise e

        self.logger.info("%i groups", len(groupIds))
        for groupId in groupIds:
            g = self.testDocumentClass(groupId, mongo=self.mongo, src=self.src)

            # CS customers only for now. I can imagine using Proactive Support
            # to sell subscriptions in the first place. If that ever happens
            # we'll give the CS customers more weight in the results.
            if not g.isCsCustomer():
                self.logger.warning("Skipping non-CS group %s", g.groupName())
                continue

            if self.args["run_tests"]:
                results = g.run_selected_tests(tests=self.args["run_tests"])
            else:
                results = g.run_all_tests()

            for testName in results:
                # If a passing test had failed previously (but has not been
                # addressed, which is why it's still listed as failed) remove
                # it from the list of failures as we'll no longer need to
                # address it ;)
                if results[testName]['pass'] is True:
                    if 'failedTests' in g.group:
                        for ft in g.group['failedTests']:
                            if ft['src'] == self.src and\
                                    ft['test'] == testName:
                                self.logger.info("Fail -> Pass! Removing %s "
                                                 "from failedTests", testName)
                                try:
                                    match = {'_id': g.groupId()}
                                    updoc = {"$pull": {self.failedTestsPath:
                                                       {"$elemMatch":
                                                        {'src': self.src,
                                                         'test': testName}}},
                                             "$inc": {'score': -1*g.
                                                      testPriorityScores[
                                                          g.tests[testName][
                                                              'priority']]}}
                                    self.coll_groups.update(match, updoc)
                                except pymongo.errors.PyMongoError as e:
                                    raise e
                    continue

                # Persist failures
                doc = {'gid': g.groupId(), 'name': g.groupName(),
                       'src': self.src, 'test': testName,
                       'ids': results[testName].get('ids', []),
                       'nids': len(results[testName].get('ids', [])),
                       'score': g.testPriorityScores[g.tests[testName][
                           'priority']]}

                try:
                    ftid = self.coll_failedtests.insert(doc)
                except pymongo.errors.PyMongoError as e:
                    raise e

                match = {'_id': g.groupId()}
                updoc = {"$addToSet": {self.failedTestsPath:
                         {'src': self.src,
                          'test': testName,
                          'ftid': ftid,
                          'score': g.testPriorityScores[g.tests[testName][
                              'priority']]}},
                         "$inc": {'score': g.testPriorityScores[g.tests[
                             testName]['priority']]}}

                if 'failedTests' in g.group:
                    for ft in g.group['failedTests']:
                        if ft['src'] == self.src and ft['test'] == testName:
                            # it's already recorded, update with the latest
                            # failedtests _id
                            match = {'_id': g.groupId(), self.failedTestsPath:
                                     {"$elemMatch":
                                      {'src': self.src,
                                       'test': testName}}}
                            ftidPath = '%s.$.ftid' % self.failedTestsPath
                            updoc = {"$set": {ftidPath: ftid}}

                try:
                    self.coll_groups.update(match, updoc)
                except pymongo.errors.PyMongoError as e:
                    raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A Euphonia test framework")

    parser.add_argument("--mongo-host", metavar="HOSTNAME",
                        default="localhost",
                        help="specify the MongoDB hostname (default="
                        "localhost)")

    parser.add_argument("--mongo-port", metavar="PORT", default=27017,
                        type=int,
                        help="specify the MongoDB port (default=27017)")

    parser.add_argument("--run-tests", metavar="TESTS", nargs="*", default=None,
                        help="run only the selected tests if this argument is present")

    parser.add_argument("src", choices=["mdiags", "mmsgroupreports", "pings"],
                        help="<-- the available test frameworks, choose one")

    args = parser.parse_args()
    t = TestFramework(args)
    t.testAllGroups()
    sys.exit(0)

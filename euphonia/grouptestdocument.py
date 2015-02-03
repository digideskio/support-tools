import logging
import pymongo


class GroupTestDocument:
    def __init__(self, groupId, mongo, src, testsLibrary=None):
        # TODO consolidate src into testsLibrary?
        # TODO remove mongo and testsLibrary from __init__?
        self.mongo = mongo
        self.src = src
        self.testsLibrary = testsLibrary

        # Use existing logger if it exists
        self.logger = logging.getLogger('logger')

        # Get group 'status' doc
        try:
            self.group = self.mongo.euphonia.groups.find_one({'_id': groupId})
        except pymongo.errors.PyMongoError as e:
            raise e

        # Supported tests
        match = {'active': True, 'src': self.src}

        try:
            curr_tests = self.mongo.euphonia.tests.find(match)
        except pymongo.errors.PyMongoError as e:
            raise e

        self.tests = {test['name']: test for test in curr_tests}
        # TODO move out of base class
        self.testPriorityScores = {'low': 2, 'medium': 4, 'high': 8}

        # Supplement with company information
        # TODO move this to a separate clienthub/sfdc library
        try:
            curr_companies = self.mongo.support.companies.find(
                {"$or": [{'jira_groups': self.groupName()},
                         {'mms_groups': self.groupName()}]})
        except pymongo.errors.PyMongoError as e:
            raise e

        if curr_companies.count() == 0:
            self.logger.warning("Company not found for group %s",
                                self.groupName())
            self.company = None
        elif curr_companies.count() > 1:
            # More than one company found... Are they the same sans _id?
            # If so, take it, otherwise complain
            # TODO replace this hack with real code
            lastCompany = None
            for company in curr_companies:
                del company['_id']
                if lastCompany is None:
                    lastCompany = company
                    continue
                if company != lastCompany:
                    lastCompany = None
                    self.logger.warning("Multiple companies found for group "
                                        " %s", self.groupName())
                    break
            self.company = lastCompany
        else:
            self.company = curr_companies.next()

    def groupId(self):
        return self.group['_id']

    def groupName(self):
        return self.group['name']

    # abstract
    def isCsCustomer(self):
        pass

    # abstract
    def next(self):
        pass

    # abstract
    def prev(self):
        pass

    def run_all_tests(self):
        self.logger.debug("run_all_tests")
        return self.run_selected_tests(self.tests)

    def run_selected_tests(self, tests):
        res = {}
        for test in tests:
            res[test] = self.run_test(test)
        return res

    def run_test(self, test):
        self.logger.debug("run_test(%s)", test)
        if test in self.tests:
            fname = "test" + test
            try:
                f = getattr(self.testsLibrary, fname)
                self.logger.debug("Testing " + test + "...")
                r = f(self)
                if r['pass'] is True:
                    self.logger.debug("Passed!")
                else:
                    self.logger.debug("Failed!")
                return r
            except AttributeError as e:
                print e
                raise Exception(fname + " not defined")
        else:
            raise Exception(test + " not defined")

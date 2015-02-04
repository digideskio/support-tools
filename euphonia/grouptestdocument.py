import logging
import pymongo


class GroupTestDocument:
    def __init__(self, groupId, mongo, src, testsLibrary=None, debug=False):
        # TODO consolidate src into testsLibrary?
        # TODO remove mongo and testsLibrary from __init__?
        self.mongo = mongo
        self.src = src
        self.testsLibrary = testsLibrary
        self.company = None

        # Use existing logger if it exists
        self.logger = logging.getLogger('logger')

        # Get group 'status' doc if it exists, otherwise create it
        try:
            query = {'_id': groupId}
            if self.groupName() is not None:
                query['name'] = self.groupName()
            updoc = {'$set': query}
            self.group = self.mongo.euphonia.groups.find_and_modify(
                query=query,
                update=updoc,
                upsert=True,
                new=True)
        except pymongo.errors.PyMongoError as e:
            raise e

        if debug:
            # Supported tests
            match = {'active': True, 'src': self.src}
        else:
            match = {'src': self.src}

        try:
            curr_tests = self.mongo.euphonia.tests.find(match)
        except pymongo.errors.PyMongoError as e:
            raise e

        self.tests = {test['name']: test for test in curr_tests}
        # TODO move out of base class
        self.testPriorityScores = {'low': 2, 'medium': 4, 'high': 8}

        # Supplement with company information if it's available
        # TODO move to a separate clienthub/sfdc library
        if self.groupName() is not None:
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
                        self.logger.warning("Multiple companies found for "
                                            "group %s", self.groupName())
                        break
                self.company = lastCompany
            else:
                self.company = curr_companies.next()

    def groupId(self):
        return self.group['_id']

    # abstract
    def groupName(self):
        pass

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
            res[test] = self.run_test(test, debug=True)
        return res

    # debug=True forces the test to run even if it's not in self.tests
    def run_test(self, test, debug=False):
        self.logger.debug("run_test(%s)", test)
        if debug or test in self.tests:
            fname = "test" + test
            try:
                f = getattr(self.testsLibrary, fname)
                self.logger.debug("Testing " + test + "...")
                r = f(self)
                if r['pass'] is True:
                    self.logger.info("Passed!")
                else:
                    self.logger.info("Failed!")
                return r
            except AttributeError as e:
                print e
                raise Exception(fname + " not defined")
        else:
            self.logger.exception(test + " not defined")
            raise Exception(test + " not defined")

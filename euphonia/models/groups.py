import pymongo

class Groups:
    """ This class manages the MMS group content.
    """

    def __init__(self, mongo):
        """ Initializes Groups class with a database object.
        :param database: MongoDB client object
        :return: None
        """
        self.db_euphonia = mongo.euphonia
        self.db_support = mongo.support
        self.coll_groups = self.db_euphonia.groups
        self.coll_failedtests = self.db_euphonia.failedtests

    def getGroupSummary(self, gid):
        """ Retrieve that needed to render the group page
        :param gid: Group ID
        :return: Dict containing everything there is to know
        """
        # High-level information
        query = {'_id': gid}
        try:
            res = self.coll_groups.find_one(query)
        except pymongo.errors.PyMongoError as e:
            raise e

        if res is not None:
            group_summary = res
        else:
            # TODO raise exception?
            group_summary = {'gid': gid}

        # Failed tests
        # This is the list of currently failed tests
        failedTests = group_summary.get('failedTests', [])
        failedTestsDict = {ft['ftid']:ft for ft in failedTests}

        # Have we created tickets for these failed tests before?
        # Return the most recent one if so
        # TODO remove this loop!
        # TODO consolidate test and src
        # TODO are we better off just querying all ticketed cases?
        for i in range(0, len(failedTests)):
            ft = failedTests[i]
            query = {'gid': gid,
                     'test': ft['test'],
                     'src': ft['src'],
                     '_id': {"$lt": ft['ftid']},
                     'ticket': {"$exists": True}}
            sort = [("_id", -1)]
            try:
                res = self.coll_failedtests.find(query).sort(sort).limit(1)
            except pymongo.errors.PyMongoError as e:
                raise e

            if res is not None:
                print("Found a previous ticket for this test!")
                test = next(res, None)
                if test is not None:
                    failedTests[i]['ticket'] = test['ticket']

        # Fetch these failed tests as we'll need their src documents
        query = {'_id': {"$in": [ft['ftid'] for ft in failedTests]}}
        try:
            res = self.coll_failedtests.find(query)
        except pymongo.errors.PyMongoError as e:
            raise e

        failedTests = []
        testDocuments = {}

        if res is not None:
            for ft in res:
                if ft['src'] not in testDocuments:
                    testDocuments[ft['src']] = []
                testDocuments[ft['src']].extend(ft['ids'])
                for key in ft.keys():
                    failedTestsDict[ft['_id']][key] = ft[key]
                failedTests.append(failedTestsDict[ft['_id']])
        else:
            # TODO raise exception?
            pass

        # Get all past failed tests that are now resolved
        query = {'gid': gid, 'resolved': {"$exists": True}}
        resolvedTests = []
        try:
            res = self.coll_failedtests.find(query)
        except pymongo.errors.PyMongoError as e:
            raise e

        for ft in res:
            resolvedTests.append(ft)
            testDocuments[ft['src']].extend(ft['ids'])

        group_summary['failedTests'] = failedTests
        group_summary['resolvedTests'] = resolvedTests

        # Fetch test documents
        ids = {}
        for key in testDocuments:
            query = {"_id": {"$in": testDocuments[key]}}
            try:
                res = self.db_euphonia[key].find(query)
            except pymongo.errors.PyMongoError as e:
                raise e

            for r in res:
                ids[r['_id'].__str__()] = r

        group_summary['ids'] = ids

        # Supplement with Clienthub info
        # TODO move this to a separate library

        if 'name' in group_summary:
            try:
                curr_companies = self.db_support.companies.find(
                        {"$or":[{'jira_groups': group_summary['name']},
                                {'mms_groups': group_summary['name']}]})
            except pymongo.errors.PyMongoError as e:
                raise e

            if curr_companies.count() == 0:
                #self.logger.warning("Error: company not found for group %s", group_summary['name'])
                #self.company = None
                group_summary['company'] = None
            elif curr_companies.count() > 1:
                # More than one company found... Are they the same sans _id?
                # If so, take it, otherwise complain
                lastCompany = None
                for company in curr_companies:
                    del company['_id']
                    if lastCompany is None:
                        lastCompany = company
                        continue
                    if company != lastCompany:
                        lastCompany = None
                        #self.logger.warning("Error: multiple companies found for group %s", self.groupName())
                        break
                #self.company = lastCompany
                group_summary['company'] = lastCompany
            else:
                #self.company = curr_companies.next()
                group_summary['company'] = curr_companies.next()

        return group_summary

    def get_failed_tests_summary(self, sort=None,
                                 skip=0, limit=10, query=None):
        """ Retrieves a list of MMS group summary docs
        :param sort: a (sort_field, sort_order) tuple
        :param skip: integer defining the number of results to skip
        :param limit: integer defining the number of results to return
        :param query: query document to filter the results
        :return: a dictionary containing the set of result group summary docs
        """
        fquery = {}
        if query is not None:
            fquery = query
        results = self.collection.find(fquery)\
                      .sort(sort)\
                      .skip(skip)\
                      .limit(limit)
        group_count = results.count()
        groups = []
        group = next(results, None)
        while group is not None:
            groups.append(group)
            group = next(results, None)
        return {"groups": groups, "count": group_count}

    def ignore_test(self, gid, test):
        """ Sets a flag in the Group summary doc to ignore a test failure
        :param gid: Group ID
        :param test: string name of the test to ignore
        :return: None
        """
        match = {"GroupId": gid, "failedTests.test": test}
        update = {"$set": {"failedTests.$.ignore": 1}}
        self.collection.update(match, update)

    def include_test(self, gid, test):
        """ Sets a flag in the Group summary doc to include a test failure
        :param gid: Group ID
        :param test: string name of the test to include
        :return: None
        """
        match = {"GroupId": gid, "failedTests.test": test}
        update = {"$set": {"failedTests.$.ignore": 0}}
        self.collection.update(match, update)

    def search(self, query):
        """ Performs an auto-complete lookup on Group Names for the search box
        :param query: Partial group name to match
        :return: Array of group summary docs
        """
        qregex = "^%s" % query
        query = {"GroupName": {"$regex": qregex, "$options": "i"}}
        project = {"GroupName": 1, "GroupId": 1, "_id": 0}
        results = self.collection.find(query, project)\
                      .sort("GroupName", 1)\
                      .limit(10)
        groups = []
        group = next(results, None)
        while group is not None:
            groups.append(group)
            group = next(results, None)
        return groups

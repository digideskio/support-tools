import bson
import pymongo
from pprint import pprint

class Groups:
    """ This class manages the MMS group content.
    """

    def __init__(self, mongo):
        """ Initializes Groups class with a database object.
        :param database: MongoDB client object
        :return: None
        """
        self.mongo = mongo
        self.db_euphonia = mongo.euphonia
        self.coll_groups = self.db_euphonia.groups
        self.coll_failedtests = self.db_euphonia.failedtests
        self.coll_pings = self.db_euphonia.pings
        self.coll_mmsgroupreports = self.db_euphonia.mmsgroupreports

    def getGroupSummary(self, gid):
        """ Retrieve that needed to render the group page
        :param gid: Group ID
        :return: Dict containing everything there is to know
        """
        # high-level information
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

        # failed tests
        # exid := example id
        failedTests = group_summary['failedTests']

        #match = {"$match": {'_id': {"$in": [ft['ftid'] for ft in failedTests]}}}
        #unwind = {"$unwind": '$ids'}
        #group = {"$group": {'_id': {'src': "$src",
        #                            'test': "$test",
        #                            'score': "$score"},
        #                    'nids': {"$sum": 1},
        #                    'exid': {"$last": "$ids"}}}
        #project = {"$project": {'src': "$_id.src",
        #                        'test': "$_id.test",
        #                        'nids': "$nids",
        #                        'exid': "$exid",
        #                        'score': "$_id.score",
        #                        '_id': 0}}

        query = {'_id': {"$in": [ft['ftid'] for ft in failedTests]}}
        proj = {'ids': {"$slice": -1}}

        try:
            #res = self.coll_failedtests.aggregate([match, unwind, group, project])
            res = self.coll_failedtests.find(query, proj)
        except pymongo.errors.PyMongoError as e:
            raise e

        failedTests = []
        pings_query_ids = []
        mmsgroupreports_query_ids = []

        if res is not None:
            for ft in res:
                if ft['src'] == "pings":
                    pings_query_ids.append(ft['ids'][0])
                elif ft['src'] == "mmsgroupreports":
                    mmsgroupreports_query_ids.append(ft['ids'][0])
                failedTests.append(ft)
        else:
            # TODO raise exception?
            pass

        group_summary['failedTests'] = failedTests

        pings_query = {"_id": {"$in": pings_query_ids}}
        mmsgroupreports_query = {"_id": {"$in": mmsgroupreports_query_ids}}

        try:
            pings_res = self.coll_pings.find(pings_query)
        except pymongo.errors.PyMongoError as e:
            raise e

        try:
            mmsgroupreports_res = self.coll_mmsgroupreports.find(mmsgroupreports_query)
        except pymongo.errors.PyMongoError as e:
            raise e

        ids = {}
        
        for r in pings_res:
            ids[r['_id'].__str__()] = r
        for r in mmsgroupreports_res:
            ids[r['_id'].__str__()] = r

        for ft in group_summary['failedTests']:
            if str(ft['ids'][0]) in ids:
                ft['ids'] = ids[str(ft['ids'][0])]
            else:
                pass

        # Supplement with Clienthub info
        # TODO move this to a separate library
        try:
            curr_companies = self.mongo.support.companies.find(
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

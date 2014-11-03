
class Groups:
    """ This class manages the MMS group content.
    """

    def __init__(self, database):
        """ Initializes Groups class with a database object.
        :param database: MongoDB client object
        :return: None
        """
        self.collection = database.groupsummaries

    def get_group_summary(self, gid):
        """ Retrieves the MMS group summary doc for a given Group ID.
        :param gid: Group ID
        :return: Dict containing a single group summary doc
        """
        query = {"GroupId": gid}
        results = self.collection.find(query)\
                      .limit(1)
        group_summary = next(results, None)
        return group_summary

    def get_failed_tests_summary(self, sort=None,
                                 skip=0, limit=10, query=None):
        """ Retrieves a list of MMS group summary docs
        :param sort: a (sort_field, sort_order) tuple
        :param skip: integer defining the number of results to skip
        :param limit: integer defining the number of results to return
        :param query: query document to filter the results
        :return: a dictionary containing the set of result documents
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
        """
        :param gid:
        :param test:
        :return:
        """
        match = {"GroupId": gid, "failedTests.test": test}
        update = {"$set": {"failedTests.$.ignore": 1}}
        self.collection.update(match, update)

    def include_test(self, gid, test):
        """
        :param gid:
        :param test:
        :return:
        """
        match = {"GroupId": gid, "failedTests.test": test}
        update = {"$set": {"failedTests.$.ignore": 0}}
        self.collection.update(match, update)

    def search(self, query):
        """
        :param query:
        :return:
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

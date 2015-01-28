import pymongo
import inspect

from mmsgroupreport_tests import MmsGroupReportTests
from groupping_tests import GroupPingTests


class Tests:
    """ This class manages the Group Report test definitions
    """
    def __init__(self, database):
        """ Initializes Tests class with a database object.
        :param database: MongoDB client object
        :return: None
        """
        self.tests_collection = database.tests

    def get_tests(self):
        """ Retrieves the set of tests defined in the database
        :return: Array of test definition documents
        """
        query = {}
        results = self.tests_collection.find(query).sort('name', pymongo.ASCENDING)
        tests = []
        result = next(results, None)
        while result is not None:
            tests.append(result)
            result = next(results, None)
        return tests

    def create_test(self, test):
        """ Adds a test definition to the database
        :param test: Dictionary that describes the test
        :return: None
        """
        self.tests_collection.insert(test)

    def update_test(self, test_name, test):
        """ Updates a test definition in the database
        :param test_name: String name of the test
        :param test: Dictionary that describes the test
        :return: None
        """
        match = {"name": test_name}
        self.tests_collection.update(match, test)

    def delete_test(self, test_name):
        """ Deletes a test definition from the database
        :param test_name: String name of the test
        :return: None
        """
        match = {"name": test_name}
        self.tests_collection.remove(match)

    @staticmethod
    def get_defined_tests():
        """ Retrieves the set of tests defined in the code
        :return: Dictionary containing the source of the defined tests
        """
        tests = {}
        module = MmsGroupReportTests()
        functions = inspect.getmembers(module)
        for key, value in functions:
            if key.startswith("test"):
                tests[key.replace("test", "")] = inspect.getsource(value)
        module = GroupPingTests()
        functions = inspect.getmembers(module)
        for key, value in functions:
            if key.startswith("test"):
                tests[key.replace("test", "")] = inspect.getsource(value)
        return tests

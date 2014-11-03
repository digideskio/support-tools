import pymongo
import inspect
import imp
# from groupreport_tests import GroupReportTests
groupreport_tests = imp.load_source('groupreport_tests', '../groupreport_tests.py')


class Tests:

    def __init__(self, database):
        self.tests_collection = database.mmsgroupreporttests

    def get_tests(self):
        query = {}
        results = self.tests_collection.find(query).sort('name', pymongo.ASCENDING)
        tests = []
        result = next(results, None)
        while result is not None:
            tests.append(result)
            result = next(results, None)
        return tests

    def create_test(self, test):
        self.tests_collection.insert(test)

    def update_test(self, test_name, test):
        match = {"name": test_name}
        self.tests_collection.update(match, test)

    def delete_test(self, test_name):
        match = {"name": test_name}
        self.tests_collection.remove(match)

    @staticmethod
    def get_defined_tests():
        module = groupreport_tests.GroupReportTests()
        functions = inspect.getmembers(module)
        tests = {}
        for key, value in functions:
            if key.startswith("test"):
                tests[key.replace("test", "")] = inspect.getsource(value)
        return tests
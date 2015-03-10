import sys, os

class Files:
    """ This class manages File uploads
    """
    def __init__(self, filename):
        """ Initializes Tests class with a database object.
        :param filename: name of the file
        :return: None
        """
        self.filename = filename

    def process_group_report(self):
        sys.argv = ['importGroupReports.py', self.filename]
        print os.path.dirname(__file__)
        os.chdir(os.path.dirname(__file__))
        os.chdir('..')
        print os.getcwd()
        execfile('importGroupReports.py')
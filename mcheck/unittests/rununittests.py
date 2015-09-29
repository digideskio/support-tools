#!/usr/bin/python
'''
System tests
'''

import glob
import os
import os.path
import sys
import unittest

_current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.normpath(os.path.join(_current_dir, '..')))

VERBOSE = False

#from mcheck import MCheckTool
import mcheck

class TestMcheck(unittest.TestCase):
    rules_dir = os.path.join(_current_dir, "data")
    rules_filenames = []

    @classmethod
    def setUpClass(cls):
        cls.rules_filenames = glob.glob(os.path.join(cls.rules_dir, "*.rul"))

    def run_one_rule_file(self, rules_filename, log_filename, log_type=mcheck.Mdiag_fmt2):
        # Runs one rules file, comparing the output to the same file with .out extension
        rules_path = os.path.join(self.rules_dir, rules_filename)
        log_path = os.path.join(self.rules_dir, log_filename)
        tool = mcheck.MCheckTool()
        tool.verbosity = 0
        rules = tool.get_rules(rules_path)
        log_obj = log_type(log_path)
        contents = log_obj.get_contents()
        ret = tool.apply_rules(rules, contents)
        if VERBOSE:
            print "\nSections: %s" % (", ".join(contents.keys()))
        return ret

    def test_kernet_open_files(self):
        ret = self.run_one_rule_file("kernel_open_files.rul", "kernel_open_files.txt", mcheck.Mdiag_fmt1)
        self.assertEqual(ret, 0)
        
    def test_os_info(self):
        ret = self.run_one_rule_file("os_info.rul", "os_info.txt", mcheck.Mdiag_fmt1)
        self.assertEqual(ret, 0)
        
    def test_os_info2(self):
        self.run_one_rule_file("os_info2.rul", "os_info2.txt")
        
    def test_proc_fmt2(self):
        self.run_one_rule_file("proc_fmt2.rul", "proc_fmt2.txt")
        
    def test_swap_fmt1(self):
        ret = self.run_one_rule_file("swap.rul", "swap_fmt1.txt", mcheck.Mdiag_fmt1)
        self.assertEqual(ret, 0)
        
    def test_swap_fmt2(self):
        ret = self.run_one_rule_file("swap.rul", "swap_fmt2.txt")
        self.assertEqual(ret, 0)
        
    # TODO add ballooning test
    
if __name__ == '__main__':
    unittest.main(verbosity=2)

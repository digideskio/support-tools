#!/usr/bin/python

import commands
import difflib
import glob
import json
import optparse
import os.path
import re
import sys

_tool_dir = os.path.dirname(os.path.abspath(__file__))
_data_dir = os.path.join(_tool_dir, "data")
_test_dir = os.path.join(_tool_dir, "test")
_test_ext = ".test"
_out_ext = ".out"
_mcheck_exe = os.path.join(_tool_dir, "..", "mcheck.py")
_diff_exe = "diff"
 
def get_opts():
    '''
    Read the options and arguments provided on the command line.
    '''
    parser = optparse.OptionParser()
    group_general = optparse.OptionGroup(parser, "General options")
    parser.add_option_group(group_general)
    group_general.add_option("-a", "--all", dest="all", action="store_true", default=False, help="run all tests")
    group_general.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False, help="show more output")
    (options, args) = parser.parse_args()
    return options, args

def get_test_args(test_file):
    fp = open(test_file)
    file_contents = json.load(fp)
    test_args = file_contents["args"]
    test_in = file_contents["infile"]
    test_out = file_contents["resfile"]
    return test_args, test_in, test_out

def get_test_name(test_file):
    start_name = len(_test_dir) + 1
    name = test_file[start_name:-5]
    return name

def run_test(test_file, verbose):
    try:
        is_pass = False
        test_name = get_test_name(test_file)
        test_dir = os.path.dirname(os.path.abspath(test_file))
        if chdir(test_dir):
            (test_args, test_in, test_res) = get_test_args(test_file)
            test_in_path = os.path.join(_data_dir, test_in)
            test_res_path = os.path.join(test_dir, test_res)
            out_path = os.path.join(test_dir, test_name + _out_ext)
            cmd = "%s %s %s > %s" % (_mcheck_exe, test_args, test_in_path, out_path)
            if verbose:
                print "  running in %s\n  %s" % (test_dir, cmd)
            run_cmd("%s 2>&1" % (cmd))
            # TODO remove previous out file
            cmd = "%s %s %s" % (_diff_exe, test_res_path, out_path)
            (diff_ret, diff_out) = run_cmd("%s 2>&1" % (cmd))
            if diff_ret == 0:
                print "-> PASS"
                is_pass = True
            else:
                if verbose:
                    print diff_out
                    print
                print "-> FAIL"
                is_pass = False
        else:
            print "Can't cd to %s" % (test_dir)
            sys.exit(2)
    except Exception, e:
        print("FATAL - issue with test\n: %s" % e.__str__())
        sys.exit(2)
    return is_pass

def chdir(path):
    ret = False
    os.chdir(path)
    new_dir = os.getcwd()
    if path == new_dir:
        ret = True
    return ret

def run_cmd(cmd, array=False, keepEOL=False):
    '''
    Run a command in the shell and return the result as a string or list
    :param cmd: command to run
    :param array: return result as array. 'True' is the default
    '''
    (status, out) = commands.getstatusoutput(cmd)
    if status:
        #raise Exception("ERROR in running - " + cmd)
        pass
    if array == True:
        if keepEOL == True:
            out = re.split('(\n)', out)    # Keep the \n
        else:
            out = out.split('\n')
    return status, out

def main():
    (options, args) = get_opts()
    errors = 0
    test_files = []
    if options.all:
        json_files = glob.glob(os.path.join(_test_dir, "*" + _test_ext))
        for one_file in json_files:
            test_files.append(one_file)
    else:
        for one_arg in args:
            one_file = os.path.join(_test_dir, one_arg + _test_ext )
            if os.path.exists(one_file):
                test_files.append(one_file)
            else:
                print "ERROR - Can't find test file %s" % (one_file)
                errors += 1
        if errors > 0:
            print "Aborting run..."
            sys.exit(2)
                
    if len(test_files) == 0:
        print("FATAL: you must provide tests as arguments, or use the --all switch")
        sys.exit(2)
    for one_testfile in test_files:
        (test_name) = get_test_name(one_testfile)
        print "\nTEST: %s" % (test_name)
        if not run_test(one_testfile, options.verbose):
            errors += 1
    print "\nThere are %d errors" % (errors)

if __name__ == '__main__':
	main()


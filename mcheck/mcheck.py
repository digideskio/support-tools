#!/usr/bin/python

'''
Created on Sept 1, 2014

@author: dcoupal
'''

from __future__ import print_function

# TODOs
# - allow to store mdiag in MongoDB
# - allow to read mdiag sections from MongoDB
# - allow to specify an error message (formatted with values) in the rule
# - test for no () match, but trying to refer to a variable in a check clause
# - all matches are case-insensitive. Is that an issue?
# - have a 'summary' group with
#   - OS, RAM
#   - list mongod with their options (removing comments)
# - check NUMA where 'mapped' = 'N0'
#    7e9efee1c000 default file=/data/lib/mongod_cdris-prd-rs2/cdris.196 dirty=18 mapped=8655 active=6247 N0=8655
# - NUMA: vm.zone_reclaim_mode = 0 <-- should be 0 if no NUMA
#   - this is wrong, mapped=259 N0=127 N1=132,  not all the mapped on the same core
# - traceAllExceptions  should not be passed as an option to mongod
# - no memory ballooning, CS-15752, charlie
# - no CPU hotplugged - CPU 2 got hotplugged, see CS-15752, section dmesg
# - reduce keepalive "net.ipv4.tcp_keepalive_time = 300" from cs-15494 , in /etc/sysctl.conf
# - ticket with a lot of mdiag outputs cs-15752
# - Linux deprioritize threads -> cat /proc/meminfo  | grep -i dirty
# - Shorten the tcp_keepalive_time to 300??? (cs-16405)
# - Set noatime and nodiratime on your devices hosting mongodb database files (cs-16405)
# - ticket CS-16342 has tons of issues, incorporate, https://jira.mongodb.org/browse/CS-16342?focusedCommentId=763620&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-763620
#   - mdiag_111314_7050AM
# - sort the check of rules to ensure test results file look similar as rules get re-organized.
# - support python rules
'''    {
        "ACTION": "Need to support $python as a rule",
        "id": "numa-0002",
        "desc": "Numa is not showing division of process threads",
        "log": "mdiag",
        "section": "proc/numa_maps",
        "example": "0195f000 default file=/localfs/mongo/mongodb/mongodb-linux-x86_64-enterprise-rhel62-2.6.4/bin/mongod anon=69 dirty=69 mapped=78 N0=69 N3=9",
        "match": "^(.*mapped=(\\d+) N.=(\\d+) N.=(\\d+))",
        "check": { "$1": { "$python": "$3 != 0 and $4 !=0" } },
        "ref": "http://docs.mongodb.org/manual/administration/production-notes/#production-numa"
    },
'''

TOOL_NAME = "mcheck"
VERSION = "1.0.0"

import json
import os.path
import optparse     # May want to consider argparse, but then would not work on Python  2.6
import re
import sys

CURRENT_DIR = os.getcwd()
HOME_DIR = os.path.expanduser("~")
TOOL_DIR = os.path.dirname(os.path.realpath(__file__))
RULES_FILENAME = TOOL_NAME + ".rul"
EMPTY = "empty"
LEVEL_3_OUTPUT_LINES = 5

class MCheckTool():

    def __init__(self):
        self.verbosity = 3
        options = None
    
    def get_options(self):
        parser = optparse.OptionParser(version="%prog " + VERSION)
        group_general = optparse.OptionGroup(parser, "General options")
        parser.add_option_group(group_general)
        group_general.add_option("-s", "--sort", dest="sort", action="store_true", default=False, help="sort results by files and rules")
        # 0=silent 1=short 2=normal 3=verbose 4=very verbose 5=debug
        group_general.add_option("-v", "--verbosity", dest="verbosity", type="int", help="show less or more output. LEVEL is 0=silent to 5=debug", metavar="LEVEL")
        group_logs = optparse.OptionGroup(parser, "Logs selection options")
        parser.add_option_group(group_logs)
        group_logs.add_option("-t", "--type", dest="type", type="string", default="", help="type of the files to process. LOGTYPE is mdiag_fmt1, mdiag_fmt2, mongod or mdiag (default)", metavar="LOGTYPE")
        group_rules = optparse.OptionGroup(parser, "Rules selection options")
        parser.add_option_group(group_rules)
        group_rules.add_option("-i", "--include", dest="include", type="string", default=None, help="Only consider those rules", metavar="RULES")
        group_rules.add_option("-e", "--exclude", dest="exclude", type="string", default=None, help="Do not consider those rules", metavar="RULES")
        group_rules.add_option("-r", "--rules", dest="rules", type="string", help="rule files to use", metavar="RULES_FILE")
        # TODO - activate once we support time base logs or output
        #group_timeline = optparse.OptionGroup(parser, "Timeline options")
        #parser.add_option_group(group_timeline)
        #group_timeline.add_option("--start", dest="start", type="string", help="starting time for considering logs entries", metavar="TIMESTAMP")
        #group_timeline.add_option("--end", dest="end", type="string", help="end time for considering log entries", metavar="TIMESTAMP")
        #group_timeline.add_option("-l", "--last", dest="last", type="string", help="use a period for the log entries (ex: 4m, 3h, 2d)", metavar="PERIOD")
        (options, args) = parser.parse_args()
        if options.verbosity:
            self.verbosity = options.verbosity
        if self.verbosity >= 6:
            print("Running Python version %s" % (sys.version))
            print("Options: %s" % (str(options)))
            print("Args: %s" % (str(args)))
        # TODO now that options are in the object, no need to pass them around
        self.options = options
        return options, args

    def add_rules(self, rules_file, rules, include_rules, exclude_rules):
        with open(rules_file) as json_file:
            json_data_unicode = json.load(json_file)
            json_data = convert_no_unicode(json_data_unicode)
            # Add all JSON to the rules, overwriting the previous ones
            rules_count = 0
            for one_rule in json_data:
                rules_count += 1
                if one_rule.has_key("id"):
                    key = one_rule["id"]
                    if self.keep_key(key, include_rules, exclude_rules):
                        rules[key] = one_rule
                else:
                    if self.verbosity >= 1:
                        print("ERROR - Could not find 'id' in rule #%d in file %s" % (rules_count, rules_file))
        # Nothing to returned, as we expect the 'rules_dict' to be modified

    def apply_rules(self, rules, contents):
        one_error_check = False
        error_check = False
        error_rule = False
        warning_rule = False
        section_names = sorted(contents.keys())
        # TODO - rules are run by their sorted order of id, may want to respect the order in the file instead
        sorted_keys = sorted(rules.keys())
        for one_rule_key in sorted_keys:
            one_rule = rules[one_rule_key]
            if self.is_complete_rule(one_rule) == False:
                if self.verbosity >= 1:
                    print("ERROR - Skipping incomplete rule %s" % (one_rule_key))
                error_rule = True
            else:
                section_name = one_rule['section']
                matching_sections = self.get_matching_sections(section_name, section_names)
                if len(matching_sections) == 0:
                    if self.verbosity >= 4:
                        print("WARNING - Skipping rule %s, section '%s' missing" % (one_rule_key, section_name))
                    warning_rule = True
                else:
                    for one_section_name in matching_sections:
                        for one_subgroup in contents[one_section_name].keys():
                            if one_subgroup == EMPTY:
                                (one_error_check, rule_status) = self.apply_rule(one_rule, contents[one_section_name][one_subgroup], section_name)
                            else:
                                (one_error_check, rule_status) = self.apply_rule(one_rule, contents[one_section_name][one_subgroup], "%s - %s" % (section_name, one_subgroup))
                            if one_error_check:
                                error_check = True
        if error_check:
            return 1
        elif error_rule:
            return 2
        elif warning_rule:
            return 3
        else:
            return 0
        
    def apply_rule(self, rule, section_hash, section_name):
        match = False
        has_check = False
        check = False
        matches = None
        all_matched_lines = []
        regex = re.compile(rule['match'], re.IGNORECASE)
        if rule.has_key('check'):
            has_check = True
            check_rule = rule['check']
        occurrence = 'sometimes'
        if rule.has_key('occurrence'):
            # TODO - check value of occurrence to see if valid
            occurrence = rule['occurrence']
        for one_line in section_hash['contents']:
            m = re.search(regex, one_line)
            if m:
                match = True
                matches = m.groups()
                if len(matches) == 0:
                    # No parenthesis in the match, report the whole line
                    one_matches_string = one_line
                else:
                    one_matches_string = ", ".join(matches)
                all_matched_lines.append(one_matches_string)
                if self.verbosity >= 5:
                    print("Match: %s" % (one_matches_string))
                if has_check and isinstance(check_rule, dict):
                    # "check": { "$1": { "$lt":7 } }
                    key1 = check_rule.keys()[0]
                    op1 = self.get_value(m, key1)
                    key11 = check_rule[key1].keys()[0]
                    val11 = check_rule[key1][key11]
                    op3 = self.get_value(m, val11)
                    # Convert first operand, if last one if int or float
                    if isinstance(op3, (int, long, float)):
                        op1 = float(op1)
                    if key11 == "$gt":
                        check = op1 > op3
                    elif key11 == "$gte":
                        check = op1 >= op3
                    elif key11 == "$eq":
                        check = op1 == op3
                    elif key11 == "$ne":
                        check = op1 != op3
                    elif key11 == "$lte":
                        check = op1 <= op3
                    elif key11 == "$lt":
                        check = op1 < op3
                    elif key11 == "$regex":
                        regex = re.compile(op3, re.IGNORECASE)
                        m = re.search(regex, op1)
                        if m:
                            check = True
                        else:
                            check = False
                    else:
                        if self.verbosity >= 2:
                            print("ERROR operand in test %s" % (check_rule))

        # 7 possible results
        # - no match from any line, but was expecting one => FAIL
        # - no match from any line
        # - match and was not expecting one => FAIL
        # - match and check fails => FAIL
        # - match and check pass
        # - match and no check and was expected
        # - match and no check => INFO we always want to see
        status = None
        status_message = ''
        
        # How many lines of matches should we display
        matches_string = '';
        if len(all_matched_lines) > 0:
            if self.verbosity >= 3:
                matches_string = "\n  ".join(all_matched_lines)
            elif self.verbosity >= 2:
                if len(all_matched_lines) > LEVEL_3_OUTPUT_LINES:
                    matches_string = "\n  ".join(all_matched_lines[0:LEVEL_3_OUTPUT_LINES]) + "\n  ..."
                else:
                    matches_string = "\n  ".join(all_matched_lines)
            else:
                matches_string = all_matched_lines[0]
        else:
            matches_string = ''
            
        if not match and occurrence == 'always':
            status = "FAIL"
            status_message = "missing line, was expecting a match"
        elif not match:
            if self.verbosity >= 4:
                status = "NOMATCH"
                status_message = "No matching line, not defined as required"
        elif match and occurrence == 'never':
            status = "FAIL"
            status_message = matches_string
        elif match and has_check and not check:
            status = "FAIL"
            status_message = matches_string
        elif match and has_check and check:
            if self.verbosity >= 3:
                status = "PASS"
                status_message = matches_string
        elif match and not has_check and occurrence == 'always':
            if self.verbosity >= 3:
                status = "INFO"
                status_message = matches_string
        elif match and not has_check:
            status = "INFO"
            status_message = matches_string

        is_error = False
        test_message = ""
        if status != None and status != "INFO" and status != "PASS":
            is_error = True
            if rule.has_key('message_fail'):
                test_message = rule['message_fail']
            else:
                test_message = rule['desc']
        else:
            if rule.has_key('message_pass'):
                test_message = rule['message_pass']
            else:
                test_message = rule['desc']
        
        if (is_error and self.verbosity >= 1) or (status != None and self.verbosity >= 4):
            print("%s - %s - %s - in %s" % (status, rule['id'], test_message, section_name))
            if self.verbosity >= 2:
                print("  %s" % (status_message))
                if self.verbosity >= 3:
                    if rule.has_key("ref"):
                        print("  See: %s" % (rule["ref"]))
                print()
    
        return(is_error, status)
    
    def get_log_obj(self, logfilename):
        log_obj = None
        if self.options.type == "":
            # Find the type
            for one_class in LOG_CLASSES:
                log_obj = one_class(logfilename)
                if log_obj.is_file_type():
                    break
                log_obj = None
        elif self.options.type == "mdiag_fmt1":
            log_obj = Mdiag_fmt1(logfilename)
        elif self.options.type == "mdiag_fmt2" or self.options.type == "mdiag":
            log_obj = Mdiag_fmt2(logfilename)

        if log_obj is None:
            fatal("Don't know the format for %s" % (logfilename))
        return log_obj
            
    def get_matching_sections(self, section_name, section_names):
        matches = []
        clean_section_name = section_name.lstrip('/')
        for one_name in section_names:
            if one_name == section_name or one_name == '/' + section_name:
                matches.append(one_name)
            elif one_name.startswith(section_name + '/') or one_name.startswith('/' + section_name + '/'):
                matches.append(one_name)
        return matches
             
    # TODO add some tests around the many rule files
    def get_rules(self, opt_rules, opt_include=[], opt_exclude=[]):
        rules_files = []
        rules = dict()
        if opt_rules == None:
            one_rule_file = os.path.join(TOOL_DIR, RULES_FILENAME)
            if os.path.isfile(one_rule_file):
                rules_files.append(one_rule_file)
            one_rule_file = os.path.join(HOME_DIR, RULES_FILENAME)
            if os.path.isfile(one_rule_file) and (CURRENT_DIR != TOOL_DIR):
                rules_files.append(one_rule_file)
            one_rule_file = os.path.join(CURRENT_DIR, RULES_FILENAME)
            if os.path.isfile(one_rule_file) and (CURRENT_DIR != TOOL_DIR) and (CURRENT_DIR != HOME_DIR):
                rules_files.append(one_rule_file)
        else:
            # Many rules files being passed as an option
            for one_rule_file in opt_rules.split(","):
                if os.path.isfile(one_rule_file):
                    rules_files.append(opt_rules)
                else:
                    if self.verbosity >= 1:
                        print("ERROR - Can't find rule file: %s" % (one_rule_file))
        if self.verbosity >= 6:
            print("Rule files: %s" % (rules_files))
        for rule_file in rules_files:
            self.add_rules(rule_file, rules, opt_include, opt_exclude)
        return(rules)
    
    def get_value(self, match, value):
        if isinstance(value, basestring):
            m = re.match(r"^\$(.+)$", value)
            if m:
                variable = m.group(1)
                m2 = re.match(r'^\d+$', variable)
                if m2:
                    value = match.group(int(variable))
                else:
                    print("ERROR - references variables not supported yet")
        return value
    
    def is_complete_rule(self, rule):
        # TOOD return a list of all missing fields instead
        is_valid = True
        fields = ['desc', 'id', 'match', 'section']
        for one_field in fields:
            if not rule.has_key(one_field):
                is_valid = False
                break
        return is_valid
    
    def keep_key(self, key, include_rules, exclude_rules):
        ret = None
        if len(exclude_rules) > 0:
            ret = True
            for one_rule in exclude_rules:
                if key.startswith(one_rule):
                    ret = False
                    break
        elif len(include_rules) > 0:
            ret = False
            for one_rule in include_rules:
                if key.startswith(one_rule):
                    ret = True
                    break
        else:
            ret = True
        return ret
        
    def run(self):
        (options, args) = self.get_options()
        include_rules = [] if options.include == None else options.include.split(",")
        exclude_rules = [] if options.exclude == None else options.exclude.split(",")
        rules = self.get_rules(options.rules, include_rules, exclude_rules)
        if self.verbosity >= 6:
            print("Rules: %s" % (rules))
        # Run rules on all output files
        ret = 0
        if len(args) == 0:
            fatal("you must provide a list of files to analyze")
        else:
            for one_log in args:
                if not os.path.isfile(one_log):
                    error("Can't open log file %s" % (one_log))
                    break
                log_obj = self.get_log_obj(one_log)
                contents = log_obj.get_contents()
                one_log_name = os.path.basename(one_log)
                print("\nAnalyzing file: %s" % (one_log_name))
                ret = self.apply_rules(rules, contents)
        return ret
           
'''
Classes for the different logs supported
'''
class Logfile():
    def __init__(self, logfilename):
        self.filename = logfilename
        self.is_type = False
        self.is_validated = False

class Mdiag_fmt1(Logfile):
    
    def is_file_type(self):
        has_line = file_has_line(self.filename, "=+ start whoami =")
        self.is_type = has_line
        self.is_validated = True
        return has_line
    
    def get_default_rules(self):
        pass
    
    def get_contents(self):
        contents = dict()
        with open(self.filename) as logfile:
            section_name = None
            subsection_name = None
            previous_section_name = None
            m = None
            line_number = 0
            for one_line in logfile.readlines():
                one_line = one_line.rstrip()
                # TODO - store the start and end line numbers of each section
                line_number += 1
                # =========== start blockdev ===========
                m = re.search(r'^=*\s*(start|end)\s+(.+?)\s+=+', one_line)
                m2 = re.search(r'^PID:\s+(\d+)$', one_line)
                m3 = re.search(r'^\-\-> (start|end)\s+(.+)\s+<\-\-$', one_line)
                if m:
                    if m.group(1) == "start":
                        if section_name != None:
                            # TODO not under a verbosity level
                            print("\nWARNING - section %s starting before end of section %s" % (m.group(2), section_name))
                        section_name =  m.group(2)
                        # the section should not exists
                        if contents.has_key(section_name):
                            # TODO not under a verbosity level
                            print("\nWARNING - more than one section with title: %s" % (section_name))
                        else:
                            contents[section_name] = {}
                            contents[section_name][EMPTY] = {}
                            contents[section_name][EMPTY]['contents'] = []
                            subsection_name = EMPTY
                    elif m.group(1) == "end":
                        section_name = None
                        subsection_name = None
                elif m2:
                    # If the first line is a PID, then we may have many sub sections
                    subsection_name = m2.group(1)
                    contents[section_name][subsection_name] = {}
                    contents[section_name][subsection_name]['contents'] = []
                    # Remove the EMPTY section
                    if contents[section_name].has_key(EMPTY):
                        del contents[section_name][EMPTY]
                elif m3 and subsection_name == EMPTY:   # Avoid being in a PID section
                    if m3.group(1) == "start":
                        previous_section_name = section_name
                        section_name = m3.group(2)
                        if contents.has_key(section_name):
                            # TODO not under a verbosity level
                            # TODO, we may want to abort instead
                            print("\nWARNING - more than one section with title: %s" % (section_name))
                        else:
                            contents[section_name] = {}
                            contents[section_name][EMPTY] = {}
                            contents[section_name][EMPTY]['contents'] = []
                            subsection_name = EMPTY
                    elif m3.group(1) == "end":
                        section_name = previous_section_name
                        subsection_name = EMPTY
                elif section_name != None:
                    try:
                        contents[section_name][subsection_name]['contents'].append(one_line)
                    except Exception, e:
                        fatal("Key error in get contents for 'Mdiag_fmt1' - line %d - section_name: %s, subsection_name: %s" % (line_number, section_name, subsection_name))
        return contents

class Mdiag_fmt2(Logfile):
    
    def is_file_type(self):
        has_line = file_has_line(self.filename, "=+ start section whoami =")
        self.is_type = has_line
        self.is_validated = True
        return has_line
    
    def get_default_rules(self):
        pass
    
    def get_contents(self):
        contents = dict()
        with open(self.filename) as logfile:
            section_name = None
            subsection_name = None
            previous_section_name = None
            m = None
            line_number = 0
            for one_line in logfile.readlines():
                one_line = one_line.rstrip()
                # TODO - store the start and end line numbers of each section
                line_number += 1
                # =========== start section blockdev ===========
                m = re.search(r'^=*\s*(start|end)\s+section\s+(.+?)\s+=+', one_line)
                m2 = re.search(r'^\-\->\s*(start|end)\s+subsection\s+\/(.+)\/(\d+)\/(.+)\s+<\-\-', one_line)
                m3 = re.search(r'^\-\->\s*(start|end)\s+subsection\s+(\/.+)\s+<\-\-', one_line)
                if m:
                    if m.group(1) == "start":
                        if section_name != None:
                            # TODO not under a verbosity level
                            print("\nWARNING - section %s starting before end of section %s" % (m.group(2), section_name))
                        section_name =  m.group(2)
                        # the section should not exists
                        if contents.has_key(section_name):
                            # TODO not under a verbosity level
                            print("\nWARNING - more than one section with title: %s" % (section_name))
                        else:
                            contents[section_name] = {}
                            contents[section_name][EMPTY] = {}
                            contents[section_name][EMPTY]['contents'] = []
                            subsection_name = EMPTY
                    elif m.group(1) == "end":
                        section_name = None
                        subsection_name = None
                elif m2:
                    if m2.group(1) == "start":
                        previous_section_name = section_name
                        section_name =  m2.group(2) + '/' + m2.group(4)
                        subsection_name = m2.group(3)
                        if not contents.has_key(section_name):
                            contents[section_name] = {}
                        if contents[section_name].has_key(subsection_name):
                            print("\nWARNING - more than one subsection with title: %s-%s" % (section_name, subsection_name))
                        else:
                            contents[section_name][subsection_name] = {}
                            contents[section_name][subsection_name]['contents'] = []
                    elif m2.group(1) == "end":
                        section_name = previous_section_name
                        subsection_name = EMPTY
                elif m3:
                    if m3.group(1) == "start":
                        previous_section_name = section_name
                        section_name = m3.group(2)
                        if contents.has_key(section_name):
                            # TODO not under a verbosity level
                            print("\nWARNING - more than one section with title: %s" % (section_name))
                        else:
                            contents[section_name] = {}
                            contents[section_name][EMPTY] = {}
                            contents[section_name][EMPTY]['contents'] = []
                            subsection_name = EMPTY
                    elif m3.group(1) == "end":
                        section_name = previous_section_name
                        subsection_name = EMPTY
                elif section_name != None:
                    try:
                        contents[section_name][subsection_name]['contents'].append(one_line)
                    except Exception, e:
                        fatal("Key error in get contents for 'Mdiag_fmt1' - line %d - section_name: %s, subsection_name: %s" % (line_number, section_name, subsection_name))
        return contents

LOG_CLASSES = [ Mdiag_fmt1, Mdiag_fmt2 ]

# Libraries

def convert_no_unicode(str_input):
    if isinstance(str_input, dict):
        return {convert_no_unicode(key): convert_no_unicode(value) for key, value in str_input.iteritems()}
    elif isinstance(str_input, list):
        return [convert_no_unicode(element) for element in str_input]
    elif isinstance(str_input, unicode):
        return str_input.encode('utf-8')
    else:
        return str_input

def file_has_line(filename, string):
    has_line = False
    fp = open(filename)
    for line in fp.readlines():
        if re.match(string, line):
            has_line = True
    fp.close()
    return has_line
    
def fatal(message):
    print("FATAL - %s" % (message))
    sys.exit(2)

def error(verbosity, message):
    if verbosity >= 1:
        print("ERROR - %s" % (message))

def log(verbosity, min_verbosity, message):
    if verbosity >= min_verbosity:
        print(message)

def stderr(*objs):
    print(*objs, file=sys.stderr)
       
def warning(verbosity, message):
    if verbosity >= 1:
        print("WARNING - %s" % (message))
        
if __name__ == '__main__':
    tool = MCheckTool()
    ret = tool.run()
    sys.exit(ret)

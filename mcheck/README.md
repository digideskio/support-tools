mcheck
======

# Overview

Script to analyze the output from [mdiag.sh](https://github.com/10gen/support-tools/raw/master/mdiag/mdiag.sh)

## Downloads:

**Latest version:** [mcheck.py](https://github.com/10gen/support-tools/raw/master/mcheck/mcheck.py)  ([Changelog](https://github.com/10gen/support-tools/commits/master/mcheck/mcheck.py))

**Do not give this script to the customers, even less the rules file**

Do **not** link to the file in the github repository, as this is a private repo that only MongoDB
employees can access.

Please note that the script is undergoing continual development, so check this repo to make sure
that the latest version is being given to users.

## See also:

[TSPROJ-42](https://jira.mongodb.org/browse/TSPROJ-42)
Owner: [Daniel Coupal](mailto:daniel.coupal@mongodb.com)


# Supported options

```
run mcheck.py --help
```

# Examples

  * Running with default rules

```  
mcheck.py mdiag_out_file
```

  * Only running the 'disk' rules

```
mcheck.py --include disk mdiag_out_file
```
    
  * Exclude all Linux distros rules (all of the form os-000N)

```
mcheck.py --exclude os-000 mdiag_out_file
```
    
  * Processing many mdiag output files

```
mcheck.py mdiag_out_file1 mdiag_out_file2 mdiag_out_file3
```

# Modifying the rules to run

```
mcheck.py --rules myrules.rul mdiag_out_file
```
  
  Will only run the rules in the *myrules.rul* file
  Otherwise, it reads the *mcheck.rul* file in the following order, the latest files overwriting rules from previous file
  
  * \<install_dir\>/myrules.rul
  * \<home_dir\>/myrules.rul
  * \<current_dir\>/myrules.rul
  
# Log levels
  
  * 0 : silent, only fatal errors
  * 1 : minimal, failing tests, only on line of output per failing rule
  * 2 : short, failing tests, but up to 5 lines (5 errors) per failing test
  * 3 : normal, failing tests, all errors per failing test
  * 4 : long, all tests being run
  * 5 : verbose, all operations being run
  * 6 : debug, even more information, mostly to debug the tool itself
  
# Running the tests

## System tests:

```
cd systemtests
# load the test data (mdiags outputs, ...)
export JIRA_USER="myjira.account"
export JIRA_PW="myjira.password"
./get_test_data.sh
./runsystemtests.py --all --verbose
```

## Unit tests

```
cd unittests
./rununittests
```

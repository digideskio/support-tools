#!/bin/bash

# Script to get the test data from the JIRA repository, or other locations.
# This is to protect the test data to be added to the Git repository, in case the repository becomes public by mistake.

# You must set JIRA_USER and JIRA_PW to your JIRA credentials

curl -u $JIRA_USER:$JIRA_PW -L https://jira.mongodb.org/secure/attachment/54920/mdiag-w1es9003.worldbank.org.txt -o ./data/1.mdiags
curl -u $JIRA_USER:$JIRA_PW -L https://jira.mongodb.org/secure/attachment/56927/mdiag_111314_7050AM_load.txt     -o ./data/2.mdiags
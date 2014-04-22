#!/usr/bin/env python 

from __future__ import print_function

from jira.client import JIRA
from jira.exceptions import JIRAError
from collections import OrderedDict

import sys
import argparse

__version__ = 0.9

field_access = {
    'key'           : lambda t: t.key,
    'priority'      : lambda t: t.fields.priority.name, 
    'assignee'      : lambda t: t.fields.assignee.displayName, 
    'status'        : lambda t: t.fields.status.name, 
    'assignee'      : lambda t: t.fields.assignee.displayName, 
    'components'    : lambda t: ', '.join( [c.name for c in t.fields.components] ),
    'created'       : lambda t: t.fields.created, 
    'description'   : lambda t: t.fields.description, 
    'fixVersions'   : lambda t: ', '.join( [f.name for f in t.fields.fixVersions] ),
    'issuetype'     : lambda t: t.fields.issuetype.name,
    'project'       : lambda t: t.fields.project.key,
    'resolution'    : lambda t: t.fields.resolution.name,
    'resolutiondate': lambda t: t.fields.resolutiondate,
    'status'        : lambda t: t.fields.status.name,
    'summary'       : lambda t: t.fields.summary,
    'versions'      : lambda t: ', '.join( [v.name for v in t.fields.versions] ) 
}


def print_table( rows, headers_stderr=True, override_headers=None, uppercase_headers=True ):
    """ rows needs to be a list of dictionaries, all with the same keys. """
    
    keys = rows[0].keys()
    headers = override_headers or keys
    if uppercase_headers:
        rows = [ dict(zip(keys, map(lambda x: x.upper(), headers))), None ] + rows
    else:
        rows = [ dict(zip(keys, headers)), None ] + rows

    lengths = [ max( len(str(row[k])) for row in rows if hasattr(row, '__iter__') ) for k in keys ]
    template = (' '*4).join( ['{%s:%i}'%(h,l) for h,l in zip(keys, lengths)] )

    for i, row in enumerate(rows):
        f = sys.stderr if i < 2 and headers_stderr else sys.stdout

        if type(row) == str:
            print(row, file=f)
        elif row == None:
            print('', file=f)
        else:
            print(template.format(**row), file=f)



def get_field_values(issue):
    """ get all the field values specified in the command line arguments and return in ordered dictionary """

    result = OrderedDict()
    for field in args['fields']:
        try: 
            result[field] = field_access[field](issue)
        except AttributeError:
            result[field] = ''
    return result


if __name__ == '__main__':

    # specify command line arguments
    argparser = argparse.ArgumentParser(description='Queries the mongodb.org JIRA instance for certain keys and prints out the specified field values in table format.')
    
    # mutually exclusive options: -q (for query) or -k (for key)
    muparser = argparser.add_mutually_exclusive_group(required=True)
    muparser.add_argument('-v', '--version', action='version', version="jira2txt version %s" % __version__)
    muparser.add_argument('-k', '--key', action='store', nargs="+", help='look up single ticket(s) by key (e.g. SERVER-12345)')
    muparser.add_argument('-q', '--query', action='store', help='use JQL query to find tickets')
    
    argparser.add_argument('-l', '--limit', action='store', metavar='L', default=50, help="only get the first L issues (requires -q, default=50)")
    argparser.add_argument('-f', '--fields', action='store', nargs='+', metavar='FIELDS', default=['key', 'summary'], choices=field_access.keys(), help="fields to print out, default is 'key summary'")

    args = vars(argparser.parse_args())

    # create jira object pointing to correct server (no auth)
    opt = {'server': 'https://jira.mongodb.org', "verify": False}
    jira = JIRA(options = opt)

    table_contents = []

    if args['key']: 
        try:
            for arg in args['key']:
                issue = jira.issue( arg, fields=','.join(args['fields']) )
                table_contents.append( get_field_values(issue) )

        except JIRAError as e:
            if e.status_code == 404:
                raise SystemExit("Jira issue %s not found" % ticket_no)
            else:
                raise SystemExit("Unknown error occured: %s" % e.text)

    elif args['query']:
        try:
            issues = jira.search_issues(args['query'], fields=','.join(args['fields']), maxResults=args['limit'] )
            for issue in issues:
                table_contents.append( get_field_values(issue) )

        except JIRAError as e:
            if e.status_code == 404:
                raise SystemExit("Jira issue %s not found" % ticket_no)
            else:
                raise SystemExit("Unknown error occured: %s" % e.text)


    print_table(table_contents)

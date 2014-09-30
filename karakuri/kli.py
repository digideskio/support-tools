#!/usr/bin/env python

import argparse
import bson.json_util
import logging
import requests
import os
import sys

from configparser import ConfigParser


class kli:
    """ A command line interface for karakuri """
    def __init__(self, args):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

        # log what your momma gave ya
        logLevel = self.args['log_level']
        logging.basicConfig()
        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logLevel)
        ch = logging.StreamHandler()
        ch.setLevel(self.args['log_level'])
        formatter = logging.Formatter('%(asctime)s - %(module)s - '
                                      '%(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        # output args for later debugging
        self.logger.debug("parsed args:")
        for arg in self.args:
            self.logger.debug("%s %s" % (arg, self.args[arg]))

        # will the real __init__ please stand up, please stand up...
        if 'live' in self.args:
            self.live = self.args['live']
        else:
            self.live = False

    def find(self, workflow):
        if workflow is not None:
            res = self.request('/workflow/%s/find' % workflow)
        else:
            res = self.request('/queue/find')

        if res['status'] == "success":
            tickets = res['data']['tickets']
        else:
            print(res['message'])
            return

        print "Found the following tickets:"
        print(tickets)

    def list(self, showInactive=False):
        res = self.request('/queue')
        if res['status'] == "success":
            tickets = res['data']['tickets']
        else:
            print(res)
            return

        print "\tTICKET ID\t\t\tISSUE KEY\tWORKFLOW\tAPPROVED?\tIN PROGRESS?\t"\
              "DONE?\tSTART\t\t\t\tCREATED"
        i = 0
        # do not show inactive tickets
        for ticket in tickets:
            if not ticket['active'] and not showInactive:
                continue
            i += 1

            # TODO suboptimal, consider adding issue key to the tickets
            res = self.request("/issue/%s" % ticket['iid'])
            if res['status'] == "success":
                issue_key = res['data']['issue']['jira']['key']
            else:
                issue_key = "UNKNOWN"

            # TODO bulletproof this
            print "%5i\t%s\t%s\t%s\t%s\t\t%s\t\t%s\t%s\t%s" %\
                  (i, ticket['_id'], issue_key, ticket['workflow'],
                   ticket['approved'], ticket['inProg'], ticket['done'],
                   ticket['start'].isoformat(),
                   ticket['_id'].generation_time.isoformat())

    def request(self, endpoint):
        url = "http://%s:%i%s" % (self.args['karakuri_host'],
                                  self.args['karakuri_port'], endpoint)
        res = requests.get(url).content
        return bson.json_util.loads(res)

    def queueAction(self, action):
        res = self.request('/queue/%s' % action)
        print("Action '%s' performed for the following tickets:" % action)
        print(res['data']['tickets'])

    def ticketAction(self, tickets, action):
        res = []
        for ticket in tickets:
            _res = self.request('/ticket/%s/%s' % (ticket, action))
            if res['status'] == 'success':
                res.append(_res['data']['ticket'])
        print("Action '%s' performed for the following tickets:" % action)
        print(tickets)

    def workflowAction(self, workflow, action):
        res = self.request('/workflow/%s/%s' % (workflow, action))
        print("Action '%s' performed for the following tickets:" % action)
        print(res['data']['tickets'])

if __name__ == "__main__":
    # Process command line arguments with a system of tubes
    parser = argparse.ArgumentParser(description="A command line interface for"
                                                 "karakuri")
    parser.add_argument("-c", "--config", metavar="FILE",
                        help="specify a configuration file")
    parser.add_argument("--log", metavar="FILE",
                        help="specify a log file")
    parser.add_argument("--log-level", metavar="LEVEL",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR",
                                 "CRITICAL"],
                        default="INFO",
                        help="{DEBUG,INFO,WARNING,ERROR,CRITICAL} "
                             "(default=INFO)")
    parser.add_argument("--karakuri-host", metavar="HOSTNAME",
                        default="localhost",
                        help="specify the karakuri hostname "
                             "(default=localhost)")
    parser.add_argument("--karakuri-port", metavar="PORT", default=8080,
                        type=int,
                        help="specify the karakuri port (default=8080)")
    parser.add_argument("-l", "--limit", metavar="NUMBER",
                        type=int,
                        help="limit process'ing to NUMBER tickets")
    parser.add_argument("--live", action="store_true",
                        help="do what you do irl")

    # This is used for cli processing, parser is used for --config
    # file processing so as not to require positional arguments
    parsers = argparse.ArgumentParser(add_help=False, parents=[parser])
    subparsers = parsers.add_subparsers(dest="command",
                                        help='{command} -h for help')

    # Sub-commands
    parser_approve = subparsers.add_parser('approve')
    parser_approve.add_argument("tickets", nargs='?',
                                help="tickets to approve (comma separated)")
    parser_approve.add_argument("--workflow", metavar="WORKFLOW",
                                help="approve all active tickets in the "
                                     "workflow")
    parser_approve.add_argument("--all", action="store_true",
                                help="approve all active tickets")

    parser_disapprove = subparsers.add_parser('disapprove')
    parser_disapprove.add_argument("tickets", nargs='?',
                                   help="tickets to disapprove (comma "
                                        "separated)")
    parser_disapprove.add_argument("--workflow", metavar="WORKFLOW",
                                   help="disapprove all active tickets in the "
                                        "workflow")
    parser_disapprove.add_argument("--all", action="store_true",
                                   help="disapprove all active tickets")

    parser_find = subparsers.add_parser('find')
    parser_find.add_argument("--workflow", metavar="WORKFLOW",
                             help="find tickets that satisfy the workflow")
    parser_find.add_argument("--all", action="store_true",
                             help="find tickets that satisfy all workflows "
                                  "(this is the default)")

    parser_list = subparsers.add_parser('list')
    parser_list.add_argument("-a', '--all", action="store_true",
                             help="include removed and completed tickets")

    parser_process = subparsers.add_parser('process')
    parser_process.add_argument("tickets", nargs='?',
                                help="tickets to process (comma separated)")
    parser_process.add_argument("--workflow", metavar="WORKFLOW",
                                help="process all active tickets in the "
                                     "workflow")
    parser_process.add_argument("--all", action="store_true",
                                help="process all active tickets")

    parser_remove = subparsers.add_parser('remove')
    parser_remove.add_argument("tickets", nargs='?',
                               help="tickets to remove (comma separated)")
    parser_remove.add_argument("--workflow", metavar="WORKFLOW",
                               help="remove all active tickets in the "
                                    "workflow")
    parser_remove.add_argument("--all", action="store_true",
                               help="remove all active tickets")

    parser_sleep = subparsers.add_parser('sleep')
    parser_sleep.add_argument("sleep", metavar="SECONDS",
                              help="sleep the ticket for SECONDS seconds")
    parser_sleep.add_argument("tickets", nargs='?',
                              help="tickets to sleep (comma separated)")
    parser_sleep.add_argument("--workflow", metavar="WORKFLOW",
                              help="sleep all active tickets in the workflow")
    parser_sleep.add_argument("--all", action="store_true",
                              help="sleep all active tickets")

    parser_wake = subparsers.add_parser('wake')
    parser_wake.add_argument("tickets", nargs='?',
                             help="tickets to wake (comma separated)")
    parser_wake.add_argument("--workflow", metavar="WORKFLOW",
                             help="wake all active tickets in the workflow")
    parser_wake.add_argument("--all", action="store_true",
                             help="wake all active tickets")

    args = parsers.parse_args()

    # Process config file if one is specified in the CLI options
    if args.config:
        args.config = os.path.abspath(os.path.expandvars(os.path.expanduser(
            args.config)))
        if not os.access(args.config, os.R_OK):
            logging.error("Unable to read config file")
            sys.exit(1)

        configParser = ConfigParser(add_help=False, fromfile_prefix_chars='@',
                                    parents=[parser])
        args = configParser.parse_args(args=["@%s" % args.config],
                                       namespace=args)

    # TODO validation up to this point
    # if not args.all:
    #    args.all = None

    k = kli(args)

    if args.command == "list":
        # k.list(args.all)
        k.list(all)

    elif args.command == "find":
        k.find(args.workflow)

    else:
        # Either specify tickets, --workflow or -all
        n = 0
        for option in [args.tickets, args.workflow, args.all]:
            if option is not None:
                n += 1

        if n != 1:
            print("Specify either tickets, --workflow or --all")
            sys.exit(2)

        # turn specified ticket or tickets into an array of tickets
        if args.tickets is not None:
            args.tickets = args.tickets.split(',')
            k.ticketAction(args.tickets, args.command)
        elif args.workflow is not None:
            k.workflowAction(args.workflow, args.command)
        elif args.all is not None:
            k.queueAction(args.command)
        else:
            print("Funny, this should never happen.")

    sys.exit(0)

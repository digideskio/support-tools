#!/usr/bin/env python

import karakuricommon
import logging
import pprint
import sys


def printRequest(request):
    if request['status'] == 'success':
        print "success, tasks affected: %i" % len(request['data'][
            'tickets'])
    elif request['status'] == 'error':
        print "error, %s" % request['message']
    elif request['status'] == 'fail':
        print "fail:"
        pprint.pprint(request['data'])
    else:
        print "error, unknown status type %s" % request['status']


class kli(karakuricommon.karakuriclient):
    """ A command line interface for karakuri """
    def __init__(self, *args, **kwargs):
        karakuricommon.karakuriclient.__init__(self, *args, **kwargs)

    def find(self, workflow):
        if workflow is not None:
            res = self.workflowRequest(workflow, 'find')
        else:
            res = self.queueRequest('find')
        if res['status'] != "success":
            self.printRequest(res)
        print "success, found %i tasks" % len(res['data']['tickets'])

    def list(self):
        res = self.queueRequest()
        if res['status'] != "success":
            self.printRequest(res)
        tickets = res['data']['tickets']

        print "\tTICKET ID\t\t\tISSUE KEY\tWORKFLOW\tAPPROVED?\tIN PROGRESS?\t"\
              "DONE?\tSTART\t\t\t\t\tCREATED"
        i = 0
        for ticket in tickets:
            i += 1
            # TODO bulletproof this
            print "%5i\t%s\t%s\t%s\t%s\t\t%s\t\t%s\t%s\t%s" %\
                  (i, ticket['_id'], ticket['key'], ticket['workflow'],
                   ticket['approved'], ticket['inProg'], ticket['done'],
                   ticket['start'].isoformat(),
                   ticket['_id'].generation_time.isoformat())

if __name__ == "__main__":
    parser = karakuricommon.karakuriparser(description="A cli interface for "
                                                       "karakuri")
    parser.add_config_argument("--karakuri-host", metavar="HOSTNAME",
                               default="localhost",
                               help="specify the karakuri hostname "
                                    "(default=localhost)")
    parser.add_config_argument("--karakuri-port", metavar="PORT", type=int,
                               default=8080,
                               help="specify the karakuri port (default=8080)")
    subparsers = parser.add_subparsers(dest="command",
                                       help='{command} -h for help')

    # Sub-commands
    parser_approve = subparsers.add_parser('approve')
    parser_approve.add_argument("tickets", nargs='?',
                                help="tickets to approve (comma separated)")
    parser_approve.add_argument("--all", action="store_true",
                                help="approve all active tickets")
    parser_approve.add_argument("--workflow", metavar="WORKFLOW",
                                help="approve all active tickets in the "
                                     "workflow")

    parser_disapprove = subparsers.add_parser('disapprove')
    parser_disapprove.add_argument("tickets", nargs='?',
                                   help="tickets to disapprove (comma "
                                        "separated)")
    parser_disapprove.add_argument("--all", action="store_true",
                                   help="disapprove all active tickets")
    parser_disapprove.add_argument("--workflow", metavar="WORKFLOW",
                                   help="disapprove all active tickets in the "
                                        "workflow")

    parser_find = subparsers.add_parser('find')
    parser_find.add_argument("--all", action="store_true",
                             help="find tickets that satisfy all workflows "
                                  "(this is the default)")
    parser_find.add_argument("--workflow", metavar="WORKFLOW",
                             help="find tickets that satisfy the workflow")

    parser_list = subparsers.add_parser('list')
    parser_list.add_argument("--all", action="store_true",
                             help="include removed and completed tickets")

    parser_process = subparsers.add_parser('process')
    parser_process.add_argument("tickets", nargs='?',
                                help="tickets to process (comma separated)")
    parser_process.add_argument("--all", action="store_true",
                                help="process all active tickets")
    parser_process.add_argument("--workflow", metavar="WORKFLOW",
                                help="process all active tickets in the "
                                     "workflow")

    parser_remove = subparsers.add_parser('remove')
    parser_remove.add_argument("tickets", nargs='?',
                               help="tickets to remove (comma separated)")
    parser_remove.add_argument("--all", action="store_true",
                               help="remove all active tickets")
    parser_remove.add_argument("--workflow", metavar="WORKFLOW",
                               help="remove all active tickets in the "
                                    "workflow")

    parser_sleep = subparsers.add_parser('sleep')
    parser_sleep.add_argument("tickets",
                              help="tickets to sleep (comma separated)")
    parser_sleep.add_argument("--all", action="store_true",
                              help="sleep all active tickets")
    parser_sleep.add_argument("--sleep", metavar="SECONDS",
                              help="sleep tickets for SECONDS seconds")
    parser_sleep.add_argument("--workflow", metavar="WORKFLOW",
                              help="sleep all active tickets in the workflow")

    parser_wake = subparsers.add_parser('wake')
    parser_wake.add_argument("tickets", nargs='?',
                             help="tickets to wake (comma separated)")
    parser_wake.add_argument("--all", action="store_true",
                             help="wake all active tickets")
    parser_wake.add_argument("--workflow", metavar="WORKFLOW",
                             help="wake all active tickets in the workflow")

    args = parser.parse_args()

    if args.log is not None:
        logger = logging.getLogger("logger")
        fh = logging.FileHandler(args.log)
        fh.setLevel(args.log_level)
        formatter = logging.Formatter('%(asctime)s - %(module)s - '
                                      '%(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # TODO validation up to this point?
    k = kli(args)

    if args.command == "list":
        k.list()
    elif args.command == "find":
        k.find(args.workflow)
    else:
        # Specify only tickets, --workflow or -all
        noptions = 0
        for option in [args.tickets, args.workflow, args.all]:
            if option:
                noptions += 1

        if noptions != 1:
            print "Specify only tickets, --workflow or --all"
            sys.exit(1)

        if args.tickets is not None:
            args.tickets = args.tickets.split(',')
            res = k.ticketsRequest(args.tickets, args.command)
        elif args.workflow is not None:
            res = k.workflowRequest(args.workflow, args.command)
        elif args.all is not None:
            res = k.queueRequest(args.command)
        else:
            print "%s is not a supported command" % args.command
            sys.exit(2)

        printRequest(res)
    sys.exit(0)

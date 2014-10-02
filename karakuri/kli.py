#!/usr/bin/env python

import karakuricommon
import logging
import pprint
import sys


def printRequest(request):
    if request['status'] == 'success':
        print "success, tasks affected: %i" % len(request['data']['tasks'])
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
            return printRequest(res)
        print "success, found %i tasks" % len(res['data']['tasks'])

    def list(self):
        res = self.queueRequest()
        if res['status'] != "success":
            return printRequest(res)
        tasks = res['data']['tasks']

        # TODO bulletproof the formatting here
        print "\tTASK ID\t\t\t\tISSUE KEY\tWORKFLOW\tAPPROVED?\tIN PROGRESS?\t"\
              "DONE?\tSTART\t\t\t\t\tCREATED"
        i = 0
        for task in tasks:
            i += 1
            print "%5i\t%s\t%s\t%s\t%s\t\t%s\t\t%s\t%s\t%s" %\
                  (i, task['_id'], task['key'], task['workflow'],
                   task['approved'], task['inProg'], task['done'],
                   task['start'].isoformat(),
                   task['_id'].generation_time.isoformat())

if __name__ == "__main__":
    parser = karakuricommon.karakuriclientparser(description="A cli interface "
                                                             "for karakuri")
    subparsers = parser.add_subparsers(dest="command",
                                       help='{command} -h for help')

    # Sub-commands
    parser_approve = subparsers.add_parser('approve')
    parser_approve.add_argument("tasks", nargs='?',
                                help="tasks to approve (comma separated)")
    parser_approve.add_argument("--all", action="store_true",
                                help="approve all active tasks")
    parser_approve.add_argument("--workflow", metavar="WORKFLOW",
                                help="approve all active tasks in the "
                                     "workflow")

    parser_disapprove = subparsers.add_parser('disapprove')
    parser_disapprove.add_argument("tasks", nargs='?',
                                   help="tasks to disapprove (comma "
                                        "separated)")
    parser_disapprove.add_argument("--all", action="store_true",
                                   help="disapprove all active tasks")
    parser_disapprove.add_argument("--workflow", metavar="WORKFLOW",
                                   help="disapprove all active tasks in the "
                                        "workflow")

    parser_find = subparsers.add_parser('find')
    parser_find.add_argument("--all", action="store_true",
                             help="find tasks that satisfy all workflows "
                                  "(this is the default)")
    parser_find.add_argument("--workflow", metavar="WORKFLOW",
                             help="find tasks that satisfy the workflow")

    parser_list = subparsers.add_parser('list')
    parser_list.add_argument("--all", action="store_true",
                             help="include removed and completed tasks")

    parser_process = subparsers.add_parser('process')
    parser_process.add_argument("tasks", nargs='?',
                                help="tasks to process (comma separated)")
    parser_process.add_argument("--all", action="store_true",
                                help="process all active tasks")
    parser_process.add_argument("--workflow", metavar="WORKFLOW",
                                help="process all active tasks in the "
                                     "workflow")

    parser_remove = subparsers.add_parser('remove')
    parser_remove.add_argument("tasks", nargs='?',
                               help="tasks to remove (comma separated)")
    parser_remove.add_argument("--all", action="store_true",
                               help="remove all active tasks")
    parser_remove.add_argument("--workflow", metavar="WORKFLOW",
                               help="remove all active tasks in the "
                                    "workflow")

    parser_sleep = subparsers.add_parser('sleep')
    parser_sleep.add_argument("tasks",
                              help="tasks to sleep (comma separated)")
    parser_sleep.add_argument("--all", action="store_true",
                              help="sleep all active tasks")
    parser_sleep.add_argument("--sleep", metavar="SECONDS",
                              help="sleep tasks for SECONDS seconds")
    parser_sleep.add_argument("--workflow", metavar="WORKFLOW",
                              help="sleep all active tasks in the workflow")

    parser_wake = subparsers.add_parser('wake')
    parser_wake.add_argument("tasks", nargs='?',
                             help="tasks to wake (comma separated)")
    parser_wake.add_argument("--all", action="store_true",
                             help="wake all active tasks")
    parser_wake.add_argument("--workflow", metavar="WORKFLOW",
                             help="wake all active tasks in the workflow")

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
        # Specify only tasks, --workflow or -all
        noptions = 0
        for option in [args.tasks, args.workflow, args.all]:
            if option:
                noptions += 1

        if noptions != 1:
            print "Specify only tasks, --workflow or --all"
            sys.exit(1)

        if args.tasks is not None:
            args.tasks = args.tasks.split(',')
            res = k.tasksRequest(args.tasks, args.command)
        elif args.workflow is not None:
            res = k.workflowRequest(args.workflow, args.command)
        elif args.all is not None:
            res = k.queueRequest(args.command)
        else:
            print "%s is not a supported command" % args.command
            sys.exit(2)

        printRequest(res)
    sys.exit(0)

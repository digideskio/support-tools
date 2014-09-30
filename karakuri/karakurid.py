#!/usr/bin/env python

import argparse
import bson.json_util
import daemon
import logging
import requests
import os
import pidlockfile
import signal
import sys
import time

from configparser import ConfigParser


class karakurid:
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

    def request(self, endpoint):
        url = "http://%s:%i%s" % (self.args['karakuri_host'],
                                  self.args['karakuri_port'], endpoint)
        res = requests.get(url).content
        return bson.json_util.loads(res)

    def run(self):
        while (1):
            self.logger.info("The Loop, the Loop, the Loop is on fire!")
            time.sleep(5)

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
    parser.add_argument("--pid", metavar="FILE",
                        default="/tmp/karakuri.pid",
                        help="specify a PID file (default=/tmp/karakuri.pid)")

    # This is used for cli processing, parser is used for --config
    # file processing so as not to require positional arguments
    parsers = argparse.ArgumentParser(add_help=False, parents=[parser])
    parsers.add_argument("command", choices=["start", "stop", "restart"],
                         help="<-- the available actions, choose one")

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

    # Who dareth summon the Daemon!? Answer me these questions three...
    pidfile = pidlockfile.PIDLockFile(args.pid)
    if args.command == "start":
        if pidfile.is_locked():
            print("There is already a running process")
            sys.exit(1)

    if args.command == "stop":
        if pidfile.is_locked():
            print("Stopping...")
            pid = pidfile.read_pid()
            os.kill(pid, signal.SIGTERM)

            sys.exit(0)
        else:
            print("There is no running process to stop")
            sys.exit(2)

    if args.command == "restart":
        if pidfile.is_locked():
            print("Restarting...")
            pid = pidfile.read_pid()
            os.kill(pid, signal.SIGTERM)
        else:
            print("There is no running process to stop")

    # Configuration error found, aborting
    error = False

    # I pity the fool that doesn't keep a log file!
    if args.log is None:
        logging.error("Please specify a log file")
        error = True
    else:
        args.log = os.path.abspath(os.path.expandvars(os.path.expanduser(
            args.log)))
        if not os.access(os.path.dirname(args.log), os.W_OK):
            logging.error("Unable to write to log file")
            error = True

    if error:
        sys.exit(2)

    # create file handler and set log level
    logger = logging.getLogger("logger")
    fh = logging.FileHandler(args.log)
    fh.setLevel(args.log_level)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(module)s - '
                                  '%(levelname)s - %(message)s')
    # add formatter to file handler
    fh.setFormatter(formatter)
    # add file handler to logger
    logger.addHandler(fh)

    context = daemon.DaemonContext(pidfile=pidfile,
                                   stderr=fh.stream, stdout=fh.stream)

    context.files_preserve = [fh.stream]
    # TODO implment signal_map

    print("Starting...")

    with context:
        k = karakurid(args)
        # redirect stderr and stdout
        # sys.__stderr__ = PipeToLogger(k.logger)
        # sys.__stdout__ = PipeToLogger(k.logger)
        k.run()

    sys.exit(0)

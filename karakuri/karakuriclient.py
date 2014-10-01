#!/usr/bin/env python

import argparse
import bson.json_util
import logging
import requests
import os
import sys

from configparser import ConfigParser


class karakuriclient:
    """ A base class for karakuri clients """
    def __init__(self, args):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

        # Log what your mother gave you
        logLevel = self.args['log_level']
        logging.basicConfig()
        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logLevel)

        # Output args for debugging
        self.logger.debug("parsed args:")
        for arg in self.args:
            self.logger.debug("%s %s" % (arg, self.args[arg]))

        if 'live' in self.args:
            self.live = self.args['live']
        else:
            self.live = False

    def request(self, endpoint):
        url = "http://%s:%i%s" % (self.args['karakuri_host'],
                                  self.args['karakuri_port'], endpoint)
        res = requests.get(url).content
        return bson.json_util.loads(res)

    def issueRequest(self, issue, command=None):
        if command is None:
            endpoint = '/issue/%s' % issue
        else:
            endpoint = '/issue/%s/%s' % (issue, command)
        return self.request(endpoint)

    def queueRequest(self, command=None):
        if command is None:
            endpoint = '/queue'
        else:
            endpoint = '/queue/%s' % command
        return self.request(endpoint)

    def ticketRequest(self, ticket, command=None):
        if command is None:
            endpoint = '/ticket/%s' % ticket
        else:
            endpoint = '/ticket/%s/%s' % (ticket, command)
        return self.request(endpoint)

    def ticketsRequest(self, tickets, command=None):
        _tickets = []
        for ticket in tickets:
            res = self.ticketRequest(ticket, command)
            if res['status'] == 'success':
                _tickets.append(res['data']['ticket'])
            else:
                return res
        return {'status': 'success', 'data': {'tickets': _tickets}}

    def workflowRequest(self, workflow, command=None):
        if command is None:
            endpoint = '/workflow/%s' % workflow
        else:
            endpoint = '/workflow/%s/%s' % (workflow, command)
        return self.request(endpoint)


class karakuriparser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        """ Process command line arguments with a system of tubes """
        # This is a non-positional argument parser that can be used for
        # --config processing
        self.parser = argparse.ArgumentParser(*args, **kwargs)
        self.parser.add_argument("--config", metavar="FILE",
                                 help="specify a configuration file")
        self.parser.add_argument("--log", metavar="FILE",
                                 help="specify a log file")
        self.parser.add_argument("--log-level", metavar="LEVEL",
                                 choices=["DEBUG", "INFO", "WARNING", "ERROR",
                                          "CRITICAL"],
                                 default="INFO",
                                 help="{DEBUG,INFO,WARNING,ERROR,CRITICAL} "
                                      "(default=INFO)")
        self.parser.add_argument("--karakuri-host", metavar="HOSTNAME",
                                 default="localhost",
                                 help="specify the karakuri hostname "
                                      "(default=localhost)")
        self.parser.add_argument("--karakuri-port", metavar="PORT", type=int,
                                 default=8080,
                                 help="specify the karakuri port "
                                      "(default=8080)")
        self.parser.add_argument("-l", "--limit", metavar="NUMBER", type=int,
                                 help="limit process'ing to NUMBER tickets")
        self.parser.add_argument("--live", action="store_true",
                                 help="do what you do irl")

        # Save in case they are needed for reinitialization
        self.kwargs = kwargs
        self.kwargs['add_help'] = False
        self.kwargs['parents'] = [self.parser]
        argparse.ArgumentParser.__init__(self, *args, **self.kwargs)

    def add_config_argument(self, *args, **kwargs):
        # Modifying parent parser requires reinitialization
        self.parser.add_argument(*args, **kwargs)
        argparse.ArgumentParser.__init__(self, **self.kwargs)

    def parse_args(self):
        args = argparse.ArgumentParser.parse_args(self)

        # Configuration error found, aborting
        error = False

        # Process config file if one is specified in the cli options
        if args.config is not None:
            args.config = os.path.abspath(os.path.expandvars(
                os.path.expanduser(args.config)))
            if not os.access(args.config, os.R_OK):
                logging.error("Unable to read config file")
                error = True

            configParser = ConfigParser(add_help=False,
                                        fromfile_prefix_chars='@',
                                        parents=[self.parser])
            args = configParser.parse_args(args=["@%s" % args.config],
                                           namespace=args)

        # I pity the fool who doesn't keep a log file!
        if args.log is not None:
            args.log = os.path.abspath(os.path.expandvars(os.path.expanduser(
                args.log)))
            if not os.access(os.path.dirname(args.log), os.W_OK):
                logging.error("Unable to write to log file")
                error = True

        if error:
            sys.exit(2)

        return args

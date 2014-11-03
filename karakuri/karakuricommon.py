#!/usr/bin/env python

import argparse
import bson.json_util
import logging
import requests
import os
import sys

from configparser import ConfigParser


class karakuribase:
    """ A base class for karakuri classes """
    def __init__(self, args):
        # Expect args from karakuriparser
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
            if "password" in arg or "passwd" in arg or "token" in arg:
                tmp = "[REDACTED]"
            else:
                tmp = self.args[arg]
            self.logger.debug("%s %s" % (arg, tmp))

        self.live = self.args['live']


class karakuriclient(karakuribase):
    """ A base class for karakuri clients """
    def __init__(self, *args, **kwargs):
        karakuribase.__init__(self, *args, **kwargs)
        self.token = self.args['token']

    def request(self, endpoint):
        url = "http://%s:%i%s" % (self.args['karakuri_host'],
                                  self.args['karakuri_port'], endpoint)
        headers = {'Authorization': "auth_token=%s" % self.token}
        res = requests.get(url, headers=headers)
        if res.status_code == requests.codes.ok:
            return bson.json_util.loads(res.content)
        else:
            message = "received HTTP status code %i" % res.status_code
            return {'status': 'error', 'message': message}

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

    def taskRequest(self, task, command=None):
        if command is None:
            endpoint = '/task/%s' % task
        else:
            endpoint = '/task/%s/%s' % (task, command)
        return self.request(endpoint)

    def tasksRequest(self, tasks, command=None):
        _tasks = []
        for task in tasks:
            res = self.taskRequest(task, command)
            if res['status'] == 'success':
                if res['data']['task'] is not None:
                    _tasks.append(res['data']['task'])
            else:
                return res
        return {'status': 'success', 'data': {'tasks': _tasks}}

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
        if len(sys.argv) == 1:
            # n00bs need help!
            args = argparse.ArgumentParser.parse_args(self, ['--help'])
        else:
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


class karakuriclientparser(karakuriparser):
    def __init__(self, *args, **kwargs):
        karakuriparser.__init__(self, *args, **kwargs)
        self.add_config_argument("--karakuri-host", metavar="HOSTNAME",
                                 default="localhost",
                                 help="specify the karakuri hostname "
                                      "(default=localhost)")
        self.add_config_argument("--karakuri-port", metavar="PORT", type=int,
                                 default=8080,
                                 help="specify the karakuri port "
                                      "(default=8080)")
        self.add_config_argument("--token", metavar="TOKEN",
                                 help="specify a CROWD user token")

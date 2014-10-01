#!/usr/bin/env python

import daemon
import karakuricommon
import logging
import os
import pidlockfile
import signal
import sys
import time


class karakurid(karakuricommon.karakuriclient):
    """ A scary karakuri daemon """
    def __init__(self, *args, **kwargs):
        karakuricommon.karakuriclient.__init__(self, *args, **kwargs)

    def run(self):
        while (1):
            self.logger.info("The Loop, the Loop, the Loop is on fire!")
            time.sleep(5)

if __name__ == "__main__":
    parser = karakuricommon.karakuriparser(description="A scary karakuri "
                                                       "daemon")
    parser.add_config_argument("--karakuri-host", metavar="HOSTNAME",
                               default="localhost",
                               help="specify the karakuri hostname "
                                    "(default=localhost)")
    parser.add_config_argument("--karakuri-port", metavar="PORT", type=int,
                               default=8080,
                               help="specify the karakuri port (default=8080)")
    parser.add_config_argument("--pid", metavar="FILE",
                               default="/tmp/karakurid.pid",
                               help="specify a PID file "
                                    "(default=/tmp/karakurid.pid)")
    parser.add_argument("command", choices=["start", "stop", "restart"],
                        help="<-- the available actions, choose one")

    args = parser.parse_args()

    # Lock it down
    pidfile = pidlockfile.PIDLockFile(args.pid)

    if args.command == "start":
        if pidfile.is_locked():
            print("There is already a running process")
            sys.exit(1)

    if args.command == "stop":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
            sys.exit(0)
        else:
            print("There is no running process to stop")
            sys.exit(2)

    if args.command == "restart":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
        else:
            print("There is no running process to stop")

    # Require a log file and preserve it while daemonized
    if args.log is None:
        print("Please specify a log file")
        sys.exit(3)

    logger = logging.getLogger("logger")
    fh = logging.FileHandler(args.log)
    fh.setLevel(args.log_level)
    formatter = logging.Formatter('%(asctime)s - %(module)s - '
                                  '%(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # This is daemon territory
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

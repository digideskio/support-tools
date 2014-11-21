## NAME
* gdbmon - uses gdb to collect stack trace samples of a running program

## SYNOPSIS
* python gdbmon.py [-h] pid [delay [count]]

## DESCRIPTION

Starts up gdb and attaches to the specified pid. Stack trace samples
are collected based on the delay and count arguments. The stack trace
samples may be analyzed using [gdbprof](gdbprof.md).

* -h, --help: show a help message
* pid: the process id of the process to trace
* delay: the amount of time to wait between samples; must be specified if a count is given.
* count: the number of samples to collect; default is 1.

## EXAMPLES

See the [README](README.md).

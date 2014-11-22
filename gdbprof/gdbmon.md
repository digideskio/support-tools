## NAME
* gdbmon - uses gdb to collect stack trace samples of a running program

## SYNOPSIS
* python gdbmon.py [-h] pid [delay [count]]

## DESCRIPTION

Starts up gdb and attaches to the specified pid. Stack trace samples
are collected based on the delay and count arguments and written to
stdout. The stack trace samples may be analyzed using
[gdbprof](gdbprof.md).

* -h, --help: show a help message
* pid: the process id of the process to trace
* delay: the amount of time to wait between samples; must be specified if a count is given.
* count: the number of samples to collect; default is 1.

Using gdb to collect stack traces can be disruptive to the system
being profiled because it stops execution of the program while it
collects stack traces. You can minimize this issue by

* allowing sufficient time between the samples (using the "delay"
  parameter) for the system to recover to equlibrium between samples
* use a stripped version of the binary being profiled. This loses
  information like line numbers and can make the traces less accurate,
  but it considerably reduces the time required to obtain the
  traces. For example in a mongod running 50 threads doing inserts,
  with a stripped binary each sample stops mongod for about 0.1-0.2
  seconds to collect the stack traces, while with an unstripped binary
  each sample takes 3-5 seconds, during which time mongod is stopped.

## EXAMPLES

See the [README](README.md).

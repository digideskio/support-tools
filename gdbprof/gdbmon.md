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
* count: the number of samples to collect. The default is 1 if no
  delay is specified; if a delay is specified samples are collected
  indefinitely until gdbmon is terminated.

Using gdb to collect stack traces can be disruptive to the system
being profiled because it stops execution of the program while it
collects the stack traces for each sample. You can minimize this issue
as follows:

* Use a stripped version of the binary being profiled. This loses
  information like line numbers and can make the traces less accurate,
  but it considerably reduces the time required to obtain the
  traces. For example in a mongod running 50 threads doing inserts,
  with a stripped binary each sample stops mongod for about 0.1-0.2
  seconds to collect the stack traces, while with an unstripped binary
  each sample takes 3-5 seconds.

* Allow sufficient time between the samples (using the "delay"
  parameter) for the system to recover to equlibrium between
  samples. A delay of at least 10 times the amount of time taken to
  collect each sample might be a good starting point.

* Take less frequent samples the more threads there are, because more
  threads increases the amount of time that the process must be
  stopped to collect stack traces for each sample, but since it
  collects more information at each sample fewer samples may be
  required to get an informative profile.

* Starting gdbmon also stops the process for a considerable length of
  time while gdb initializes, so it should only be started once,
  ideally at a point where a stoppage of the process is not harmful,
  for example before initiating a test. You can use the --after and
  --before parameters of [gdbprof](#gdbprof.md) to select a portion of
  the samples collected to analyze.

## EXAMPLES

See the [README](README.md).

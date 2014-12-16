## NAME
* gdbprof - generic timeseries visualization tool

## SYNOPSIS
* python timeseries.py [--width WIDTH] [--height HEIGHT] [--show-empty] [--show-zero] [--no-merges] [--number-rows] [--duration DURATION] [--after AFTER] [--before BEFORE] [--every EVERY] [--level {1,2,3,4,5,6,7,8,9}] [--list] what:where [what:where ...]

## DESCRIPTION

* --width WIDTH: width of each graph in characters; default 30.
* --height HEIGHT: of each graph in lines; default 1.8.
* --show-empty: show graphs even if there is no corresponding data
* --show-zero: show graphs even if all data is 0
* --no-merges: don't merge statistics onto a single graph.
* --number-rows: number each row
* --duration DURATION: limit each graph to the specified duration in seconds.
* --after AFTER: plot only data after the specified time.
* --before BEFORE: plot only data before the specified time.
* --every EVERY: interval in seconds between data points to plot.
* --level {1-9}: initial detail level; default: 1.
* --list: list the available metrics and exit

The data to plot is specified by additional arguments of the form what:where, where 
* what specifies the metric to be extracted from the file, and
* where is the file.

The specified metric is matched against the available metrics using a fuzzy matching algorithm that breaks the specified and available metric name into words (ignoring punctuation), and looks for available metrics with words that match the specified metric. Matches with words in the correct order and matches at the beginning of the name of the available metric are preferred.

The list of available metrics can be viewed by using the --list option, but see the example below for a simpler way to get started.


## EXAMPLES

Here's a simple example to get started. Collect some data as follows:

    mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep(1000)}" >ss.log &
    iostat -t -x 1 >iostat.log &

When you have collected as much data as desired, terminate the data collection processes, for example

    killall mongo iostat

Then visualize the results as follows:

    python timeseries.py ss:ss.log iostat:iostat.log mongod:mongod.log >timeseries.html
    open timeseries.html

This will select
* all metrics whose name begins with "ss" (which stands for serverStatus) from ss.log, because by convention all metrics found in a serverStatus log have names that begin with ss; and
* all metrics whose name begins with "iostat" from iostat.log, and
* all metrics whose name begins with "mongod" from mongod.log.

The initial view will be restricted to the most important (level 1) statisics; you can interactively request more detailed statistics.

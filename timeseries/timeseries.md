## NAME
* timeseries - generic timeseries visualization tool

## SYNOPSIS
* python timeseries.py [--width WIDTH] [--height HEIGHT] [--show-empty] [--show-zero] [--no-merges] [--number-rows] [--duration DURATION] [--after AFTER] [--before BEFORE] [--every EVERY] [--relative] [--level {1,2,3,4,5,6,7,8,9}] [--list] [--server] [--browser] [--port PORT] [--connect URL] [--live SECONDS] what:where [what:where ...]

## DESCRIPTION

* --width WIDTH: width of each graph in characters; default 30.
* --height HEIGHT: of each graph in lines; default 1.8.
* --show-empty: show graphs even if there is no corresponding data
* --show-zero: show graphs even if all data is 0
* --no-merges: don't merge metrics onto a single graph.
* --number-rows: number each row
* --duration DURATION: limit each graph to the specified duration in seconds.
* --after AFTER: plot only data after the specified time.
* --before BEFORE: plot only data before the specified time.
* --every EVERY: interval in seconds between data points to plot.
* --relative: show timestamps relative to start of timeline
* --level {1-9}: initial detail level; default: 1.
* --list: list the available metrics and exit
* --server: open in server mode, listening for connections on the specified PORT (default 8888)
* --browser: open in server mode, and then open a browser window connecting to the server
* --connect: open a browser and connect it to the specified server, opening a view as specified by the other command line options
* --live: refresh view periodically at specified interval, specfied in seconds (default 0, which means no refresh)

The data to plot is specified by additional arguments of the form what:where, where 
* what specifies the metric to be extracted from the file, and
* where is the file.

The specified metric is matched against the available metrics using a fuzzy matching algorithm that breaks the specified and available metric name into words (ignoring punctuation), and looks for available metrics with words that match the specified metric. Matches with words in the correct order and matches at the beginning of the name of the available metric are preferred.

The list of available metrics can be viewed by using the --list option, but see the example above for a simpler way to get started.

See the [quickstart guid](quickstart.md) for some usage scenarios focused on ftdc data (mongod diagnostics.data directory).



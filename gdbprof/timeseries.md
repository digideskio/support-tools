## Timeseries Visualization Tool

Here's a simple example to get started. Collect some data as follows:

    delay=1 # pick a number in seconds
    mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep(1000*$delay)}" >ss.log &
    iostat -k -t -x $delay >iostat.log &

When you have collected as much data as desired, terminate the data collection processes, for example

    killall mongo iostat

Install timeseries.py pre-reqs:

    sudo pip install -r requirements.txt

Then visualize the results as follows:

    python timeseries.py ss:ss.log iostat:iostat.log mongod:mongod.log >timeseries.html
    open timeseries.html

This will select
* all metrics whose name begins with "ss" (which stands for serverStatus) from ss.log, because by convention all metrics found in a serverStatus log have names that begin with ss; and
* all metrics whose name begins with "iostat" from iostat.log, and
* all metrics whose name begins with "mongod" from mongod.log.

The initial view will be restricted to the most important (level 1) statisics; you can interactively request more detailed metrics, as described in the help text included with the graphs.

### About the browser

I use mostly Chrome, and have seen some issues on Safari. For now please use Chrome to view the .html file if possible.

### Performance of the tool

Large data sets will 1) take a long time to process and 2) generate html files that may overwhelm the browser. Working on improvements, but for now to avoid this issue try specifying (for example) --every 300 on the command line to only look at log entries every 5 minutes, to get an overview; and then select a region to view in more detail and use --after and --before. NOTE: when you specify --every it will simply ignore some of the input. For cumulative counters that is ok because it in effect gives you an averaged view, but for events (e.g. long queries in mongod, or checkpoints running in ss) it may simply miss some events, so be careful when interpreting graphs generated using --every.

### Timezones

The iostat output uses timestamps that don't include a timezone; timeseries.py will assume the local timezone of the machine where timeseries.py is installed. If this is different from the timezone of the machine where iostats.log was collected, you will see that the iostats don't line up with the other logs, so you will need to specify the timezone in effect on the machine where iostats.log was collected. For example, if that machine is on PST, specify:

    python timeseries.py "ss:ss.log" "iostat(tz=-8):iostat.log" "mongod:mongod.log" >timeseries.html
    open timeseries.html

### Selecting metrics from the command line

If you are doing the same groupings over and over, e.g. want to script it, it becomes worthwhile to select just the stats you want on the command line. The "ss:", "iostat:", and "mongod:" strings above are actually just abbreviations that will match all metrics beginning with "ss", "iostat", and "mongod". To make a more specific selection you can say for example:

    python timeseries.py "iostat cpu:iostat.log"                        # shows all iostat cpu metrics
    python timeseries.py "iostat cpu user:iostat.log"                   # shows only user cpu time
    python timeseries.py "cpu user:iostat.log"                          # same as above - names are matched using a fuzzy algorithm
    python timeseries.py "cpu user:iostat.log" "cpu system:iostat.log"  # specify same file multiple times to select multiple groups


## REFERENCE

### NAME
* gdbprof - generic timeseries visualization tool

### SYNOPSIS
* python timeseries.py [--width WIDTH] [--height HEIGHT] [--show-empty] [--show-zero] [--no-merges] [--number-rows] [--duration DURATION] [--after AFTER] [--before BEFORE] [--every EVERY] [--level {1,2,3,4,5,6,7,8,9}] [--list] what:where [what:where ...]

### DESCRIPTION

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
* --level {1-9}: initial detail level; default: 1.
* --list: list the available metrics and exit

The data to plot is specified by additional arguments of the form what:where, where 
* what specifies the metric to be extracted from the file, and
* where is the file.

The specified metric is matched against the available metrics using a fuzzy matching algorithm that breaks the specified and available metric name into words (ignoring punctuation), and looks for available metrics with words that match the specified metric. Matches with words in the correct order and matches at the beginning of the name of the available metric are preferred.

The list of available metrics can be viewed by using the --list option, but see the example above for a simpler way to get started.



## Quickstart guide for using timeseries tool with ftdc

### Prerequisites

* The timeseries tool requires Python 2.7.

* You can install the prequisite packages using the following command:

        sudo pip install argparse python-dateutil pytz

* For now, Google Chrome is required.

* Currently OSX and Linux are supported.

### Collecting and visualizing timeseries data for mongod 3.0

The remainder of this document assumes the new full-time data capture
facility in mongod 3.2, which automatically collects serverStatus and
other metrics at one-second intervals. This section describes how to
collect and visualize similar data under 3.0. Skip this section if you
have a diagnostic.data directory from 3.2.

You can collect data similar to the 3.2 ftdc data under 3.0 by using
an external process:

    delay=1 # pick a number in seconds
    mongo --eval "while(true) {print(JSON.stringify(db.serverStatus({tcmalloc:true}))); sleep(1000*$delay)}" >ss.log &

You can then use all of the commmands and interactive capabilities
described in the remainder of the document, substituting "ss.log"
for "diagnostic.data" on the command line, for example:

    python timeseries.py ss.log --browser 

### Automatic interactive browser/server mode

If you have a copy of a diagnostic.data directory from a mongod, for
example from a customer or a test system, the simplest way to view it
is to use browser/server mode, specifying the diagnostic.data
directory name on the command line, for example:

    python timeseries.py diagnostic.data --browser 

This starts the timeseries tool in server mode, visualizing ftdc data
in the diagnostic.data directory, and then automatically pops open a
browser window that connects to the timeseries server. Interactive
browser/server mode supports additional interactive features such as
zooming and opening new views that are not supported if you generate
and view a static html file.

### Manual interactive browser/server mode specifying view at the server

The preceding example is essentially equivalent to the following two
steps, where in the second step you manually open a browser window
rather than asking the timeseries tool to do it for you.

    python timeseries.py --server $dbpath/diagnostic.data
    open http://localhost:8888

You may find this useful under some circumstances, depending on your
workflow. For example, you might start the server on a remote machine
where you are running a test, and connect to it from a browser on your
local machine; in this case you would substitute the remote machine
name for "localhost".

### Manual interactive browser/server mode specifying view at the client

As an alternative to the above you can use the following:

    python timeseries.py --server
    python timeseries.py $dbpath/diagnostic.data --connect http://localhost:8888

The first step starts a server, but does not specify the view. In the
second step you specify the view and the server that you wish to
connect to, and the timeseries tool pops open a browser window giving
it a request based on your specified view that will connect to the
specified server and retrieve that view. Using this approach you can
open multiple views, for example on different data sources or with
different command-line parameters.

### Offline mode

In offline mode you generate an html file and then open a browser to view it:

    python timeseries.py $dbpath/diagnostic.data >timeseries.html
    open timeseries.html

This mode supports a limited subset of the interactive features
available in browser/server mode.

### Interactive features in offline and browser/server modes

Cursors are useful to look for correlated events, and to label them for discussion:

* click on a graph to put down a cursor line
* click on a blue disk to delete a cursor

You can rearrange the rows to bring the relevant graphs to the top for
better viewing:

* click on a name to select a row
* ^N select the next row 
* ^P select the previous row 
* n move the selected row down 
* p move the selected row up 
* N move the selected row to the bottom 
* P move the selected row to the top 

The default detail level is the minimum, 1; detail level 4 contains
most useful information.

* 1-9 to change detail level

### Interactive features in browser/server mode only

To zoom in to a specific time range, place one or more cursors, then
hit z; you will be prompted for which cursor range to zoom into.

* z to zoom in
* Z to zoom out

You can obtain detailed info, including either the values as
displayed, or the raw underlying metrics, at a seleted time. Typically
the values as displayed will be more meaningful; for example,
cumulative counts in the raw underlying metrics are differentiated to
obtain rates for the values as displayed.

* ? to get values as displayed
* ! to get raw underlying metrics

Some groups of related statistics, such as operations rates, are
normally color-coded and grouped (merged) together in a single
graph. You can override this behavior.

* m to suppress merging related statistics into a single graph
* M to enable merging related statistics into a single graph (this is the default)

You can open new views, either in the current window or a new window.

* o to open new view in current window
* O to open new view in new window

The o and O commands open a dialog where you specify the new view as
you would on the command line, including [command-line view
options](timeseries.md) such as graph width, graph height, show
empty and uniformly 0 graphs, don't show multiple metrics on a single
graph, and so on.  Multiple views maintain their own state, so for
example you can have different views on the same data zoomed in to
different time ranges.

You can view live data by pointing the timeseries tool at the
diagnostic.data directory of a running mongod instance. Caching and
lazy decompression will be used to make this efficient. You can
manually referesh the view by hitting RETURN.

* RETURN to refresh the view with current values of live data

You can also enable automatic periodic refresh when viewing live
data. You will be prompted for a refresh interval in seconds. The
default value of 10 seconds corresponds the default mongod period for
saving ftdc data. Specify 0 to disable live mode.

* l to enable periodic refresh of live data

In order to display large amounts of data with reasonable performance,
the overview tool will automatically lower the effective sampling rate
for larger data sets. This will do a good job of displaying average
values at a lower resolution, but as a result can miss fast events. In
order to see all data you can zoom in using "z" as described above, or
you can use the "v" command to select the number of overview samples
to show; specify "all" show all samples.

* v to select the number of samples to display

### Opening new views

As described above, there are two ways you can open new views:

* Use the timeseries tool and specify the server to connect to with
  the --connect command-line option. The view to open is specified by
  the other command-line options. This approach can be used to open
  new views under script control.

* Use the o and O interactive commands in an existing view.

### Viewing live data

You can specify a $dbpath/diagnostic.data for a live mongod instance
to see updated statistics in semi-real time. The timeseries tool uses
a combination of caching and lazy decompression of the ftdc data to
make this reasonably efficient. You can do this by manually refreshing
the view using the browser refresh button, or you can enable live mode
as described above to periodically refresh the view.

### Viewing mongod log data

You can view mongod log data along with other sources of timeseries
data by adding "mongodb.log" to the command line, for example:

    python timeseries.py mongodb.log diagnostic.data --browser 

This will display information about the following:

* Number of logged slow operations per second

* Length of longest slow operation, in ms, during each second

This information is displayed both for all operations in total, and
broken out by namespace and operation.


### Collecting and viewing system information (iostat)

It is sometimes useful to have system information such as disk and CPU
usage, along with mongod internal data. This is not currently captured
by the full-time data capture facility of mongod, although it may be
in the future. For now you can capture it as follows:

    delay=1 # pick a number in seconds
    iostat -k -t -x $delay >iostat.log &

Then you can visualize it along with the ftdc data by adding
"iostat(tz=...):iostat.log" to your command line, for example:

    python timeseries.py "iostat(tz=-5):iostat.log" diagnostic.data --browser 

Since iostat does not capture timezone information, you will need to
specify it on the command line, as illustrated above for EST.

(The part preceding the colon in "iostat(tz=-5):iostat.log" is a
timeseries descriptor that specifies the type of the file; it has been
omitted from the other examples in this guide because for most file
types the timeseries tool is able to determine the file type by
inspection.)

Similarly, under 3.0 you can collect iostat data alongside the
serverStatus data:

    delay=1 # pick a number in seconds
    mongo --eval "while(true) {print(JSON.stringify(db.serverStatus({tcmalloc:true}))); sleep(1000*$delay)}" >ss.log &
    iostat -k -t -x $delay >iostat.log &

And then visualize both iostat.log and ss.log together:

    python timeseries.py "iostat(tz=-5):iostat.log" ss.log --browser 


### Collecting and visualizing additional user-defined timeseries data

You can visualize arbitrary data stored in a csv file alongside other
timeseries data. For example, to investigate file size growth, create
a csv file "las.csv" recording the file size over time as follows:

    fn=/ssd/db/r0/WiredTigerLAS.wt
    (
        echo "time,size"
        while true; do
            echo "$(date --rfc-3339=ns),$(stat --format '%s' $fn)"
            sleep 1
        done
    ) >/ssd/db/r0/las.csv

Then visualize the ftdc data alongside the file size data:

    python timeseries.py /ssd/db/r0/{las.csv,diagnostic.data} --browser

The csv file must have a field called "time" that contains
timezone-aware timestamps in a format understood by Python
dateutil.parser.parse, or Unix timestamps (which are assumed to be
UTC). All remaining fields must be numeric, and each will be displayed
on a separate graph.





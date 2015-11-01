## Quickstart guide for using timeseries tool with ftdc

### Automatic interactive browser/server mode

If you have a copy of a diagnostic.data directory from a mongod, for
example from a customer or a test system, the simplest way to view it
is to use browser/server mode, specifying the diagnostic.data
directory name on the command line, for example:

    python timeseries.py ftdc:diagnostic.data --browser 

This starts the timeseries tool in server mode, visualizing ftdc data
in the diagnostic.data directory, and then automatically pops open a
browser window that connects to the timeseries server. Interactive
browser/server mode supports additional interactive features such as
zooming and opening new views that are not supported if you generate
and view a static html file.

(Note: for now, only Chrome is support for the browser, on OSX and Linux.)


### Manual interactive browser/server mode specifying view at the server

The preceding example is essentially equivalent to the following two
steps, where in the second step you manually open a browser window
rather than asking the timeseries tool to do it for you.

    python timeseries.py --server ftdc:$dbpath/diagnostic.data
    open http://localhost:8888

You may find this useful under some circumstances, depending on your
workflow. For example, you might start the server on a remote machine
where you are running a test, and connect to it from a browser on your
local machine; in this case you would substitute the remote machine
name for "localhost".

### Manual interactive browser/server mode specifying view at the client

As an alternative to the above you can use the following:

    python timeseries.py --server
    python timeseries.py ftdc:$dbpath/diagnostic.data --connect http://localhost:8888

The first step starts a server, but does not specify the view. In the
second step you specify the view and the server that you wish to
connect to, and the timeseries tool pops open a browser window giving
it a request based on your specified view that will connect to the
specified server and retrieve that view. Using this approach you can
open multiple views, for example on different data sources or with
different command-line parameters.

### Offline mode

In offline mode you generate an html file and then open a browser to view it:

    python timeseries.py ftdc:$dbpath/diagnostic.data >timeseries.html
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

You can obtain detailed info, including specific values of raw
metrics, at a seleted time.

* ? to get detailed raw info at a selected time

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

You can enable periodic refresh for viewing live data. You will be
prompted for a refresh interval in seconds. The default value of 10
seconds corresponds the default mongod period for saving ftdc
data. Specify 0 to disable live mode.

* l to enable periodic refresh of live data

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




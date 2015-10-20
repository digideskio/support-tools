## Quickstart guide for using timeseries tool with ftdc

### Automatic interactive browser/server mode

If you have a copy of a diagnostic.data directory from a mongod, for example from a customer or a test system, the simplest way to view it is to use browser/server mode, specifying the diagnostic.data directory name on the command line, for example:

    python timeseries.py ftdc:diagnostic.data --browser 

This starts the timeseries tool in server mode, visualizing ftdc data in the diagnostic.data directory, and then automatically pops open a browser window that connects to the timeseries server. Interactive browser/server  mode supports additional interactive features such as zooming and opening new views that are not supported if you generate and view a static html file.

(Note: for now, only Chrome is support for the browser, on OSX and Linux.)


### Manual interactive browser/server mode specifying view at the server

The preceding example is essentially equivalent to the following two steps, where in the second step you manually open a browser window rather than asking the timeseries tool to do it for you. 

    python timeseries.py --server ftdc:$dbpath/diagnostic.data
    open http://localhost:8888

You may find this useful under some circumstances, depending on your workflow. For example, you might start the server on a remote machine where you are running a test, and connect to it from a browser on your local machine; in this case you would substitute the remote machine name for "localhost".

### Manual interactive browser/server mode specifying view at the client

As an alternative to the above you can use the following:

    python timeseries.py --server
    python timeseries.py ftdc:$dbpath/diagnostic.data --connect http://localhost:8888

The first step starts a server, but does not specify the view. In the second step you specify the view and the server that you wish to connect to, and the timeseries tool pops open a browser window giving it a request based on your specified view that will connect to the specified server and retrieve that view.

### Offline mode

In offline mode you generate an html file and then open a browser to view it:

    python timeseries.py ftdc:$dbpath/diagnostic.data >timeseries.html
    open timeseries.html

This mode supports a limited subset of the interactive features available in browser/server mode.

### Interactive features in offline and browser/server modes

Cursors are useful to look for correlated events, and to label them for discussion:

* click on a graph to put down a cursor line
* click on a blue disk to delete a cursor
* click on a name to select a row

You can rearrange the rows to bring the relevant graphs to the top for better viewing:

* ^N select the next row 
* ^P select the previous row 
* n move the selected row down 
* p move the selected row up 
* N move the selected row to the bottom 
* P move the selected row to the top 

The default detail level is the minimum, 1; detail level 4 contains most useful information.
* 1-9 to change detail level

### Interactive features in browser/server mode only

To zoom in to a specific time range, place one or more cursors, then hit z; you will be prompted for which cursor range to zoom into.
* z to zoom in
* Z to zoom out

You can open new views, either in the current window or a new window. You specify the view in the dialog as you would on the command line, including options such as "--no-merges".
* o to open new view in current window
* O to open new view in new window



## Simple gdb-based profiling tool

This is a simple gdb-based profiling tool, similar in spirit to [Poor
Man's Profiler](http://poormansprofiler.org/), but a little
fancier. The problem addressed is that most profiling tools see only
CPU execution time and don't see time spent waiting for things like
i/o and locks. This tool improves on the simple Poor Man's Profiler
approach in two ways:

* it starts up gdb only once, and then scripts it to collect the stack
  traces, reducing overhead.
* it includes a tool that aggregates stack traces into call trees to
  give a little more informative view of where the time is being
  spent.

Here's a simple example to get started, based on the issue reported in
[SERVER-16235](https://jira.mongodb.org/browse/SERVER-16235). First,
we reproduce the issue, and then collect some profile data using
gdbmon:

    python gdbmon.py $(pidof mongod) 1 10 >example.gdbmon

This fires up gdb to collect 10 stack trace samples at 1 second
intervals. Now analyze the results, focusing only on stack traces that
include initAndListen or handleIncomingMsg:

    python gdbprof.py -j 'handleIncomingMsg|initAndListen' <example.gdbmon

This produces the following output:

    10 samples, 120 traces, 12.00 threads
    avg.thr max.thr  call tree
       1.00    1.00  main:664
       1.00    1.00   mongoDbMain:848
       1.00    1.00    mongo::initAndListen:615
       1.00    1.00     _initAndListen:610
       1.00    1.00      mongo::Listener::initAndListen:256
       1.00    1.00       select
       1.00    1.00  clone
       1.00    1.00   start_thread
       1.00    1.00    mongo::PortMessageServer::handleIncomingMsg:234
       1.00    1.00     mongo::MyMessageHandler::process:190
       1.00    1.00      mongo::assembleResponse:390
       1.00    1.00       receivedQuery:220
       1.00    1.00        mongo::newRunQuery:549
       1.00    1.00         runCommands:131
       1.00    1.00          mongo::_runCommands:1498
       1.00    1.00           mongo::Command::execCommand:1423
       1.00    1.00            mongo::_execCommand:1209
       1.00    1.00             mongo::WriteCmd::run:144
       1.00    1.00              mongo::WriteBatchExecutor::executeBatch:265
       1.00    1.00               mongo::WriteBatchExecutor::bulkExecute:756
       1.00    1.00                mongo::WriteBatchExecutor::execInserts:873
       0.90    1.00                ├mongo::WriteBatchExecutor::execOneInsert:1078
       0.90    1.00                │ insertOne:1051
       0.90    1.00                │  singleInsert:1107
       0.90    1.00                │   mongo::Collection::insertDocument:196
       0.90    1.00                │    mongo::Collection::_insertDocument:235
       0.80    1.00                │    ├mongo::WiredTigerRecordStore::insertRecord:507
       0.80    1.00                │    │ mongo::WiredTigerRecordStore::cappedDeleteAsNeeded:403
       0.80    1.00                │    │  __curfile_next:79
       0.80    1.00                │    │   __wt_btcur_next:439
       0.80    1.00                │    │    __cursor_row_next:279
       0.80    1.00                │    │     __wt_txn_read:173
       0.60    1.00                │    │      __wt_txn_visible:119
       0.10    1.00                │    └mongo::WiredTigerRecordStore::insertRecord:498
       0.10    1.00                │      __curfile_insert:211
       0.10    1.00                │       __wt_btcur_insert:492
       0.10    1.00                │        __cursor_row_modify:263
       0.10    1.00                │         __wt_row_modify:205
       0.10    1.00                │          __wt_insert_serial:264
       0.10    1.00                │           __wt_cache_page_inmem_incr:50
       0.10    1.00                │            __wt_page_is_modified:25
       0.10    1.00                └mongo::WriteBatchExecutor::execOneInsert:1084
       0.10    1.00                  mongo::finishCurrentOp:638
       0.10    1.00                   mongo::logger::LogstreamBuilder::~LogstreamBuilder:123
       0.10    1.00                    mongo::logger::LogDomain<...>::append:60
       0.10    1.00                     mongo::logger::RotatableFileAppender<...>::append:63
       0.10    1.00                      std::ostream::flush
       0.10    1.00                       std::basic_filebuf<...>::sync
       0.10    1.00                        std::basic_filebuf<...>::overflow
       0.10    1.00                         std::basic_filebuf<...>::_M_convert_to_external
       0.10    1.00                          ??
       0.10    1.00                           write
    
* We collected 120 stack traces over our 10 samples, indicating that
  there were 12 threads running.

* Of those our filter serves to select two threads: the main thread
  and a pthread, represented by the two call trees, one rooted in
  main() and the other rooted in clone().

* The call tree shows the average and maximum number of threads
  executing at each call site over the course of the run.

* The main thread is spending all of its time in select() waiting for
  a new connection. This is wait time that would be invisible to
  CPU-based profiling tools.

* The other thread shown is servicing incoming messages on a
  connection, and is spending most of its time in cappedDeleteAsNeeded
  at line 403 calling __curfile_next. This begins to pinpoint the
  problem.

* Each function is annotated with the line number within that
  function, which means that if a given function calls another
  function twice it will show up as two separate branches of the
  tree. This gives the most information about what calls are
  responsible for performance issues, but the line numbers can be
  suppressed with the -l flag if you wish to count all calls to a
  given callee from a given caller in the same bucket.

* Note that our sampling also caught the connection thread waiting in
  write for i/o to the mongod log, probably logging a slow op. This
  would have been invisible to CPU-based profiling tools. (We would
  need to collect more samples to determine how significant an impact
  this has on performance.)

### Interact HTML profile view with graphical timeline

You can generate an interactive HTML profile for viewing in your
browser. An example taken from
[SERVER-16355](https://jira.mongodb.org/browse/SERVER-16355). This
command produces the view shown below.

    gdbprof -j handleIncomingMsg --html -g 10 --graph-scale log <example.gdbmon >example.html
    open example.html

When the generated HTML is viewed in a browser the tree can be
interactively pruned to focus on the parts of interest. The -g option
adds a timeline next to each call site showing the number of threads
executing at that call site at each point in time. Here we see a
correlation in time between the two call sites highlighted by the
notes (added using Preview), giving us a clue as to the source of the
bottleneck.

<img src="example.png" width="5in"></img>







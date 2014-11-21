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

    10 samples, 119 traces, 11.90 threads
    count    thr  stack
       10   1.00  main:664
       10   1.00   mongoDbMain:848
       10   1.00    mongo::initAndListen:615
       10   1.00     _initAndListen:610
       10   1.00      mongo::Listener::initAndListen:256
       10   1.00       select
       10   1.00  clone
       10   1.00   start_thread
       10   1.00    mongo::PortMessageServer::handleIncomingMsg:234
       10   1.00     mongo::MyMessageHandler::process:190
       10   1.00      mongo::assembleResponse:390
       10   1.00       receivedQuery:220
       10   1.00        mongo::newRunQuery:549
       10   1.00         runCommands:131
       10   1.00          mongo::_runCommands:1498
       10   1.00           mongo::Command::execCommand:1423
       10   1.00            mongo::_execCommand:1209
       10   1.00             mongo::WriteCmd::run:144
       10   1.00              mongo::WriteBatchExecutor::executeBatch:265
       10   1.00               mongo::WriteBatchExecutor::bulkExecute:756
       10   1.00                mongo::WriteBatchExecutor::execInserts:873
        9   0.90                 mongo::WriteBatchExecutor::execOneInsert:1078
        9   0.90                  insertOne:1051
        9   0.90                   singleInsert:1107
        9   0.90                    mongo::Collection::insertDocument:196
        9   0.90                     mongo::Collection::_insertDocument:235
        8   0.80                      mongo::WiredTigerRecordStore::insertRecord:507
        8   0.80                       mongo::WiredTigerRecordStore::cappedDeleteAsNeeded:403
        8   0.80                        __curfile_next:79
        8   0.80                         __wt_btcur_next:439
        8   0.80                          __cursor_row_next:279
        8   0.80                           __wt_txn_read:173
        6   0.60                            __wt_txn_visible:119
        1   0.10                      mongo::WiredTigerRecordStore::insertRecord:498
        1   0.10                       __curfile_insert:211
        1   0.10                        __wt_btcur_insert:492
        1   0.10                         __cursor_row_modify:263
        1   0.10                          __wt_row_modify:205
        1   0.10                           __wt_insert_serial:264
        1   0.10                            __wt_cache_page_inmem_incr:50
        1   0.10                             __wt_page_is_modified:25
        1   0.10                 mongo::WriteBatchExecutor::execOneInsert:1084
        1   0.10                  mongo::finishCurrentOp:638
        1   0.10                   mongo::logger::LogstreamBuilder::~LogstreamBuilder:123
        1   0.10                    mongo::logger::LogDomain<...>::append:60
        1   0.10                     mongo::logger::RotatableFileAppender<...>::append:63
        1   0.10                      std::ostream::flush()
        1   0.10                       std::basic_filebuf<...>::sync()
        1   0.10                        std::basic_filebuf<...>::overflow(int)
        1   0.10                         std::basic_filebuf<...>::_M_convert_to_external(char*, long)
        1   0.10                          ??
        1   0.10                           write
    
* We saw on average 11.90 threads in execution over the course of
  collecting the 10 samples.

* Of those our filter selects two threads - the main thread and a
  pthread, represented by the two call trees, one rooted in main() and
  the other rooted in clone().

* The main thread is spending all of its time in select() waiting for
  a new connection. This is wait time that would be invisible to
  CPU-based profiling tools.

* The other thread shown is servicing incoming messages on a
  connection, and is spending most of its time in
  cappedDeleteAsNeeded. This begins to pinpoint the problem.

* Note that our sampling also caught the connection thread waiting for
  i/o to the mongod log, probably logging a slow op. This would have
  been invisible to CPU-based profiling tools. (We would need to
  collect more samples to determine how significant an impact this has
  on performance.)



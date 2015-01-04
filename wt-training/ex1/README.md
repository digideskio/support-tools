This exercise is based on
[CAP-1787](https://jira.mongodb.org/browse/CAP-1787) and
[SERVER-16546](https://jira.mongodb.org/browse/SERVER-16546):
unexpected memory growth was observed on 2.8.0-rc2 while running a
YCSB workload. The memory growth appeared to start some time after the
WT cache filled up.

### Reproducing the problem

* Download 2.8.0-rc2

* Start up a standalone instance using the WT storage engine. We'll
  want a small cache since issue seems to be associated with filling
  cache. Ticket says 1 GB, I used 500 MB. You'll have you'll have to
  use an older command-line interface for this since we're using rc2:

        mongod --storageEngine wiredTiger --wiredTigerEngineConfig=cache_size=500MB ...

* Start system stats monitoring. For this exercise we'll need generic
  server stats, and the WT engine global stats. You can otain both of
  those with this command, which does a serverStatus every 0.5 seconds:

        mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep(0.5*1000)}" >ss.log &

* Start 10 threads of a heavy insert workload based on the [mongo
  shell
  repro](https://jira.mongodb.org/browse/SERVER-16546?focusedCommentId=788101&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-788101)
  found by Darren Wood. Here's my adaptation of his repro (following
  is one thread, you'll need 10):

        function repro(thread) {
        
            var seed = thread + 1;
            function randomString(len) {
                var rv = '';
                while (len > 0) {
                    var x = Math.sin(seed++) * 10000;
                    rv += (x - Math.floor(x));
                    len -= 20;
                }
                return rv;
            }
            
            count = 500000
            every = 10000
            for (var i=0; i<count; ) {
                var bulk = db.c.initializeUnorderedBulkOp();
                for (var j=0; j<every; j++, i++)
                    bulk.insert({'_id': randomString(100), 'payload': randomString(1000)});
                try {
                    bulk.execute();
                    print(i)
                } catch (e) {}
            }
        }

* When it finishes, terminate the stats collection.

* Copy the stats you collected, ss.log, back to your workstation, and
  visualize them as follows:

        python timeseries.py 'ss:ss.log' >repro.html
        open -a 'Google Chrome' repro.html

  Note that if a significant time elapsed between when you started
  collecting the stats and when you started the workload you may want
  to use the --after flag to timeseries.py to focus on the relevant
  part of the timeline, for example

        python timeseries.py --after 10:00 ...

  If the local machine and target machine timezone differ you'll need
  to specify that in the time (e.g. "Z" for UTC, -0500 for EST)

* Have you reproduced the issue? How can you tell? What stats are relevant here?


### Some things to observe and explain

* ss mem: virtual (MB)
* ss mem: resident (MB)
* ss wt cache: pages evicted because they exceeded the in-memory maximum (/s)
* ss wt reconciliation: split bytes currently awaiting free (MB)
* ss wt transaction: transaction checkpoint currently running
* ss wt cache: pages currently held in the cache
* ss wt cache: eviction server evicting pages (/s)
* ss wt reconciliation: page reconciliation calls for eviction (/s)

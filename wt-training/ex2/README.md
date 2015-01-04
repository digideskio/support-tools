This exercise is based on
[SERVER-16247](https://jira.mongodb.org/browse/SERVER-16247) where we
saw declining performance over time in rc1 in a replica set, but not
standalone. After some experimentation, we reduced the size and time
of the repro by determining that
* the problem occurred in a single node replica set
* the problem occurred more quickly with a small oplog

### Reproducing the problem

* Download 2.8.0-rc1. (NOTE: the ticket was originally reported for
  rc0, but the problem still existed in rc1, and for this exercise
  it's important to use rc1 in order to get the required metrics.)

* Start up a single node replica set using the WT storage engine with
  a 50 MB oplog.

* Start system stats monitoring. For this exercise we'll need generic
  server stats, and the WT engine global stats. You can otain both of
  those with this command, which does a serverStatus every 1.0 seconds:

        mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep(1.0*1000)}" >ss.log &

* Since the problem seems to be related to the oplog, we'll want stats
  for the oplog. You can obtain those with the following command:

        mongo local --eval "
            while(true) {
                s = db.oplog.rs.stats()
                s.time = new Date()
                print(JSON.stringify(s))
                sleep(1.0*1000)
            }
        " >cs.log &
                
* For the "advanced" part of this exercise we'll look at gdb stack
  trace samples, collected at 2-second intervals.

      sudo python gdbmon.py $(pidof mongod) 2 >gdbmon.log &

* Start the workload. This is designed to put a large number of
  documents into the oplog as quickly as possible, without creating a
  large collection.

        function repro() {
        
            db.c.drop()
            db.c.insert({_id:0, i:0})
         
            count = 1500000
            every = 10000
            for (var i=0; i<count; ) {
                var bulk = db.c.initializeOrderedBulkOp();
                for (var j=0; j<every; j++, i++)
                    bulk.find({_id:0}).updateOne({_id:0, i:i})
                bulk.execute();
                print(i)
            }
        }

* When it finishes, terminate the stats collection.

        killall mongo
        sudo killall gdb

* Copy the stats you collected, *.log, back to your workstation, and
  visualize them as follows:

        python timeseries.py 'ss:ss.log' 'cs:cs.log' >repro.html
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

* ss opcounters ...
* cs cursor ...
* ss wt btree ... (NOTE: this has been renamed in a later rc to "ss wt cursor ...")
* ss wt connection: total write read I/Os (/s)
* ss wt log: log write operations (/s)
* ss wt transaction: transactions committed (/s)

### Advanced: gdb stack trace samples

* Visualize the gdb stack trace samples collected above, together with
  the update stats:

        python $tools_dir/timeseries/gdbprof.py -g 10 --graph-scale log --html \
            --series 'ss opcounters update:ss.log' <gdbmon.log >gdbmon.html
        open -a 'Google Chrome' gdbmon.html

  You may wish to use the --after flag if there is signficant "dead"
  time at the beginning when stats collection was running before the
  test started.

* Look for call sites that are correlated with the slowdown. Any
  hypotheses?
            

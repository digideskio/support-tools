This exercise is based on
[SERVER-16651](https://jira.mongodb.org/browse/SERVER-SERVER-16651)
where we observed a performance problem related to TTL collections
under WiredTiger. The performance problem was specific to WT in a
replica set.

### Reproducing the problem

* Download 2.8.0-rc4.

* Start up a 1-node replica set.

* Start system stats monitoring. For this exercise we'll need generic
  server stats, and the WT engine global stats. You can otain both of
  those with this command, which does a serverStatus every 0.5 seconds:

        mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep(0.5*1000)}" >ss.log &

* For the "advanced" part of this exercise we'll look at gdb stack
  trace samples, collected at 2-second intervals.

      sudo python gdbmon.py $(pidof mongod) 2 >gdbmon.log &

* Start a workload that creates ttl collection and inserts documents
  into it for two minutes.

        function repro() {
        
            var every = 10000
            var duration = 120
            
            db.c.drop();
            db.c.ensureIndex({ttl: 1}, {expireAfterSeconds: 30});
            
            t0 = new Date()
            var i = 0;
            while (new Date() - t0 < duration*1000) {
                var bulk = db.c.initializeUnorderedBulkOp();
                for (var j=0; j<every; i++, j++)
                    bulk.insert({ttl: new Date()})
                bulk.execute();
                print(i)
            }
        }

* When it finishes, terminate the stats collection.

        killall mongo
        sudo killall gdb

* Copy the stats you collected, *.log, back to your workstation, along
  with mongod log (calling it "db.log" here), and visualize them as
  follows:

        python $tools_dir/timeseries/timeseries.py \
            'ss:ss.log' 'mongod(bucket_size=0.1):db.log' >repro.html
        open -a 'Google Chrome' repro.html

  Note that if a significant time elapsed between when you started
  collecting the stats and when you started the workload you may want
  to use the --after flag to timeseries.py to focus on the relevant
  part of the timeline, for example

        python timeseries.py --after 10:00 ...

  If the local machine and target machine timezone differ you'll need
  to specify that in the time (e.g. "Z" for UTC, -0500 for EST)

* Have you reproduced the issue? How can you tell? What stats are relevant here?

* What does this have to do with TTL? Is it more general? Can you
  demonstrate that?


### Some things to observe and explain

* ss opcounters ...
* ss metrics ttl ...
* mongod max logged query (ms) per 0.1s
* ss wt cursor ...

### Advanced: gdb stack trace samples

* Visualize the gdb stack trace samples collected above, together with
  the update stats:

        python $tools_dir/timeseries/gdbprof.py -g 10 --graph-scale log --html \
            --series 'ss opcounters update:ss.log' <gdbmon.log >gdbmon.html
        open -a 'Google Chrome' gdbmon.html

  You may wish to use the --after flag if there is signficant "dead"
  time at the beginning when stats collection was running before the
  test started.

* Look for call sites that are correlated with the issue. Any hypotheses?

* What does this have to do with WT??

            

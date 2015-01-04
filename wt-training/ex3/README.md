This exercise is based on
[SERVER-16662](https://jira.mongodb.org/browse/SERVER-16662) (and
several other related tickets) where we observed occasional extended
pauses with 0 throughput under heavy load. The journal and the oplog
introduce their own performance issues and complexity into the
picture, but even without those there is an interesting and important
effect to observe, so for this exercise we will focus on the
standalone (no oplog), no-journal case.


### Reproducing the problem

* Build the [workload
  generator|https://jira.mongodb.org/browse/SERVER-16269?focusedCommentId=788373&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-788373]
  due to John Page. Instructions for Ubuntu:

        sudo apt-get install -y gcc libtool autoconf
        git clone https://github.com/mongodb/mongo-c-driver
        (cd mongo-c-driver; ./autogen.sh --libdir=/usr/lib; make; sudo make install)
        git clone https://github.com/johnlpage/WorkLoad
        (cd WorkLoad; make)

* Download 2.8.0-rc4.

* Start up a standalone mongod with no journal.

* Start system stats monitoring. For this exercise we'll need generic
  server stats, and the WT engine global stats. You can otain both of
  those with this command, which does a serverStatus every 0.1 seconds:

        mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep(0.1*1000)}" >ss.log &

* System CPU and disk utilization statistics will prove interesting in
  this case, so let's collect those, also at 0.1 second
  intervals. You'll need sysmon.py from support-tools/timeseries:

        python sysmon.py 0.1 >sysmon.log &

* For the "advanced" part of this exercise we'll look at gdb stack
  trace samples, collected at 1-second intervals.

      sudo python gdbmon.py $(pidof mongod) 1 >gdbmon.log &

* Start the workload using the workload generator we built
  above. We'll need a heavy load, so let's start 100 clients, and run
  for 60 seconds:

        WorkLoad/loadsrv -h 'localhost:27017' -p 100 -d 60

* When it finishes, terminate the stats collection.

        killall mongo
        pkill -f sysmon.py
        sudo killall gdb

* Copy the stats you collected, *.log, back to your workstation, along
  with mongod log (calling it "db.log" here), and visualize them as
  follows:

        python $tools_dir/timeseries/timeseries.py  >repro.html \
            'ss:ss.log' 'sysmon:sysmon.log' 'mongod(bucket_size=0.1):db.log'
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
* why the periodic dips in op througput?
* ss active read/write queue
* mongod maxed loged query per 0.1 s
* sysmon cpu user/systm
* sysmon context switches
* ss wt block-manager ...
* ss wt cache: pages read into written from cache
* ss wt connection: total write read I/O
* ss wt cache: eviction server ...

### Advanced: gdb stack trace samples

* Visualize the gdb stack trace samples collected above, together with
  the update stats:

        python $tools_dir/timeseries/gdbprof.py -g 10 --graph-scale log --html \
            --series 'ss opcounters update:ss.log' <gdbmon.log >gdbmon.html
        open -a 'Google Chrome' gdbmon.html

  You may wish to use the --after flag if there is signficant "dead"
  time at the beginning when stats collection was running before the
  test started.

* Look for call sites that are correlated with the pauses. Any
  hypotheses?
            

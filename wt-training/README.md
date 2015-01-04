### Presentation outline

* [file format tour](../mdb-wt/tour.md)

* tools
    * data collection
        * [standard](https://jira.mongodb.org/browse/SERVER-16699?focusedCommentId=796325&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-796325)
        * gdbmon
    * data analysis
        * timeseries.py
        * wtstats.py        
        * gdbprof.py
        * OSX heap (?)
    * data sources
        * cpu (iostat, sysmon.py)
        * disk (iostat, sysmon.py)
        * server status (db.serverStatus())
        * wt global stats (db.serverStatus(), --...)
        * collection stats (db.c.stats())
        * wt collection stats (db.c.stats.wiredTiger)
        * mongod log file
        * oplog


### Exercises

Series of hands-on exercises based on SERVER tickets that I worked on over recent weeks:
* [ex1](ex1)
* [ex2](ex2)
* [ex3](ex3)
* ...

The exercises assume the following:

* Linux machine (I'll call it "target machine"), preferably Ubuntu, to
  run the repros on - I mostly use Ubuntu on a VMware VM on my local
  workstation. Should also work with an AWS instance. My VMware
  instance has 6 cores, 8 GB memory, 50 GB disk.

* On the target machine we'll do some "advanced" exercises involving
  collecting and visualizing gdb stack traces samples. Note that this
  is useful for in-house repros, and possibly for some customers on
  test systems, but is *not* suitable for use on customer production
  system! Set up (on Ubuntu) is as follows:

        sudo apt-get install gdb
        echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope # allows gdb to attach

* On your local workstation (where you run your browser) obtain and
  set up pre-requisites for viz tooling:

        git clone http://github.com/10gen/support-tools
        sudo pip install -f support-tools/timeseries/requirements.txt

  If you had already downloaded the support-tools repo in the past,
  please be sure to update now to pick up some recent tooling fixes.

* Chrome is preferred browser for vis tools: https://www.google.com/chrome/browser/desktop/index.html

Each exercise directory has the following structure:

* **README.md** describes the exercise, including steps to do the repro
  and collect the data to look at.

* **run.sh** is a script that you can use to run the entire repro if you
  want, starting on your local workstation. It copies the needed stuff
  to the target machine, runs the repro, copies the output files back,
  and visualizes them. Configure for your directory structure at the
  top of the script. I wrote these scripts to test the scenarios, and
  to serve as a guide if you get stuck. Feel free to use as much or as
  little of this as you want.

* **repro.sh** is the part of the repro that runs on the target machine.

* **result/** directory is what I got when I ran the repro on my
  setup. Refer to this for comparison, or if all else fails and you
  can't get the repro to work just look at this data.



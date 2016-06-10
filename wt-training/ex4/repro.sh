#
# download rc4
#
release=mongodb-linux-x86_64-2.8.0-rc4
wget http://fastdl.mongodb.org/linux/$release.tgz
tar xf $release.tgz
PATH=$release/bin:$PATH

#
# start mongod 1-node repl set
#
killall -9 mongod; rm -rf db; mkdir -p db
while pgrep mongod; do sleep 1; done
mongod --dbpath db --logpath db.log --replSet rs --fork --storageEngine wiredTiger
mongo --eval 'rs.initiate(); while (rs.status().myState!=1) sleep(1000)'

#
# start serverStatus monitoring every 0.5 seconds
# leaves output in ss.log
#
mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep(0.5*1000)}" >ss.log &

#
# start gdbmon monitoring every 2 seconds
# this is for the "advanced" part of the exercise
# requires that gdb be installed
# may have permissions issues on Ubuntu:
#    simple fix is to run as root
#    or: echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope
#        and then run as same user as mongod
# useful for in-house repros, and possibly for some customers on test systems
# *not* suitable for use on customer production system!
#
sudo python gdbmon.py $(pidof mongod) 2 >gdbmon.log &

#
# run the test
#
mongo --eval "load('repro.js'); repro()"


#
# terminate monitoring
#
killall mongo
sudo killall gdb


    




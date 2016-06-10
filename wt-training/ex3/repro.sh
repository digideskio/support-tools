#
# build load generator
#
sudo apt-get install -y gcc libtool autoconf
git clone https://github.com/mongodb/mongo-c-driver
(cd mongo-c-driver; ./autogen.sh --libdir=/usr/lib; make; sudo make install)
git clone https://github.com/johnlpage/WorkLoad
(cd WorkLoad; make)

#
# download rc4
#
release=mongodb-linux-x86_64-2.8.0-rc4
wget http://fastdl.mongodb.org/linux/$release.tgz
tar xf $release.tgz
PATH=$release/bin:$PATH

#
# start standalone mongod with no journal
#
killall -9 mongod; rm -rf db; mkdir -p db
while pgrep mongod; do sleep 1; done
mongod --dbpath db --logpath db.log --nojournal --storageEngine wiredTiger --fork

#
# start serverStatus monitoring every 0.1 seconds
# leaves output in ss.log
#
mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep(0.1*1000)}" >ss.log &

#
# start sysmon monitoring every 0.1 seconds
# leaves output in sysmon.log
#
python sysmon.py 0.1 >sysmon.log &

#
# start gdbmon monitoring every 1 seconds
# this is for the "advanced" part of the exercise
# requires that gdb be installed
# may have permissions issues on Ubuntu:
#    simple fix is to run as root
#    or: echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope
#        and then run as same user as mongod
# useful for in-house repros, and possibly for some customers on test systems
# *not* suitable for use on customer production system!
#
sudo python gdbmon.py $(pidof mongod) 1 >gdbmon.log &

#
# start the load
# -p 100: 100 processes
# -d 60: 60-second run
#
WorkLoad/loadsrv -h 'localhost:27017' -p 100 -d 60


#
# terminate monitoring
#
killall mongo
pkill -f sysmon.py
sudo killall gdb


    




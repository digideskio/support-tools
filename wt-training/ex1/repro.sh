#
# download rc2
#
release=mongodb-linux-x86_64-2.8.0-rc2
wget http://fastdl.mongodb.org/linux/$release.tgz
tar xf $release.tgz
PATH=$release/bin:$PATH

#
# start mongod with 500 MB WT cache
# NOTE: --wiredTigerEngineConfig was superseded by "whitelisted" WT command line options after rc2
#
killall -9 mongod; rm -rf db; mkdir -p db
while pgrep mongod; do sleep 1; done
mongod --dbpath db --logpath db.log --fork \
    --storageEngine wiredTiger --wiredTigerEngineConfig=cache_size=500MB

#
# start serverStatus monitoring every 0.5 seconds
# leaves output in ss.log
#
mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep(0.5*1000)}" >ss.log &


#
# start 10 of them and wait
#
(
    for t in $(seq 10); do
        mongo --eval "load('repro.js'); repro($t)" &
    done
    wait
)

#
# terminate monitoring
#
killall mongo


    




import mdocker
from mdocker import wait_until_up, wait_to_become_primary, MDocker
import pymongo
from pymongo import MongoClient
import collections
from timeit import default_timer as timer
from pymongo import ReadPreference
import time

#create an instance of MDocker
docker = MDocker()

# create new system (image, params, sleep time)
deploy = collections.OrderedDict()
default_image = "alex/mongodb_26_auth_ent"
deploy["mongo_D1"] = (default_image, "mongod --sslMode preferSSL --sslPEMKeyFile /usr/local/bin/cert.pem --smallfiles --replSet xxx --keyFile /usr/local/bin/keyfile", 27017)
deploy["mongo_D2"] = (default_image, "mongod --sslMode preferSSL --sslPEMKeyFile /usr/local/bin/cert.pem --smallfiles --replSet xxx --keyFile /usr/local/bin/keyfile", 27017)
deploy["mongo_CFG1"] = (default_image, "mongod --sslMode preferSSL --sslPEMKeyFile /usr/local/bin/cert.pem --smallfiles --keyFile /usr/local/bin/keyfile", 27017)
deploy["mongo_CFG2"] = (default_image, "mongod --sslMode preferSSL --sslPEMKeyFile /usr/local/bin/cert.pem --smallfiles --keyFile /usr/local/bin/keyfile", 27017)
deploy["mongo_CFG3"] = (default_image, "mongod --sslMode preferSSL --sslPEMKeyFile /usr/local/bin/cert.pem --smallfiles --keyFile /usr/local/bin/keyfile", 27017)
deploy["mongo_S1"] = (default_image, "mongos --sslMode preferSSL --sslPEMKeyFile /usr/local/bin/cert.pem --configdb mongo_CFG1:27017,mongo_CFG2:27017,mongo_CFG3:27017 --keyFile /usr/local/bin/keyfile", 27017)

res = docker.deploy(deploy)
if res != 1:
	print("Failed deploying. Aborting")
	docker.cleanup()
	sys.exit(2)

# initialize it
replSetConfig = {
     "_id" : "xxx",
     "members" : [
         {"_id" : 0, "host" : "mongo_D1", "priority" : 10},
         {"_id" : 1, "host" : "mongo_D2"}
     ]
}

print("Init replica set..")
docker.local_mongo_shell('mongo_D1','rs.initiate(' + str(replSetConfig) + ')')
wait_to_become_primary('mongo_D1', 27017)

print("Creating users..")
docker.local_mongo_shell('mongo_D1','db.getSisterDB(\'admin\').createUser({ user: \'admin\', pwd: \'password\', roles: [ \'root\' ]})')
docker.local_mongo_shell('mongo_S1','db.getSisterDB(\'admin\').createUser({ user: \'admin\', pwd: \'password\', roles: [ \'root\' ]})')

#print("Init replica set..")
#client = MongoClient('mongo_D1', 27017)
#client.admin.authenticate('admin', 'password')
#client.admin.command('replSetReconfig', replSetConfig)
#
#wait_to_become_primary('mongo_D1', 27017)


print("Sharding the collection..")
client = MongoClient('mongo_S1', 27017, read_preference=ReadPreference.PRIMARY_PREFERRED)
client.admin.authenticate('admin', 'password')
client.admin.command('addShard', 'xxx/mongo_D1')
client.admin.command('enableSharding', 'test')
client.admin.command('shardCollection', 'test.test', key={'_id': 1})

client.admin.command('setParameter', 1, logLevel=5)

print("Napping just in case...")
time.sleep(5)
exit()

client['test'].test.insert(deploy)

for x in range(0, 5):
	print("Running iteration " + str(x))
	start = timer()
	print(client['test'].test.find_one())
	ts = timer() - start
	print("Time: " + str(ts))
	time.sleep(6)

docker.block("mongo_D1")
print("Napping 30 sec")
time.sleep(30)

for x in range(0, 5):
        print("Running iteration " + str(x))
        start = timer()
        print(client['test'].test.find_one())
        ts = timer() - start
        print("Time: " + str(ts))
        time.sleep(6)

print("Done")

# cleanup
docker.cleanup()


/*
Requirements:
- Java
- mtools mlaunch (optional)

mlaunch --sharded 2 --config 1 --replicaset

How to run this:
javac -cp .:mongo-java-driver-2.11.3.jar MongoShardedClusterCountDirectly.java && java -cp .:mongo-java-driver-2.11.3.jar: MongoShardedClusterCountDirectly

Sample output:
--- Sharding Status ---
  sharding version: { "_id" : 1 , "version" : 3 , "minCompatibleVersion" : 3 , "currentVersion" : 4 , "clusterId" : { "$oid" : "52398d88ddd2302687498b37"}}
  shards:
{ "serverUsed" : "localhost/127.0.0.1:27024" , "shards" : [ { "_id" : "shard01" , "host" : "shard01/localhost:27017,localhost:27018,localhost:27019"} , { "_id" : "shard02" , "host" : "shard02/localhost:27020,localhost:27021,localhost:27022"}] , "ok" : 1.0}
connecting to localhost:27017,localhost:27018,localhost:27019
count: 86124
connecting to localhost:27020,localhost:27021,localhost:27022
count: 35344
each shard total count: 121468
mongos total count: 121468

*/

import com.mongodb.BasicDBObject;
import com.mongodb.CommandResult;
import com.mongodb.DB;
import com.mongodb.DBCollection;
import com.mongodb.DBObject;
import com.mongodb.MongoClient;
import com.mongodb.MongoClientURI;

import java.util.List;

public class MongoShardedClusterCountDirectly {

    public static void main(String[] args) throws Exception {

        // connect to the local mongoS
        MongoClient m = new MongoClient( "localhost" , 27024 );

        DB configDB = m.getDB( "config" );
        DB db = m.getDB( "admin" );

        DBCollection configVersion = configDB.getCollection("version");
        if (configVersion.findOne() == null) {
            System.out.println( "printShardingStatus: this db does not have sharding enabled. be sure you are connecting to a mongos from the shell and not to a mongod." );
        }

        System.out.println( "--- Sharding Status --- " );
        System.out.println( "  sharding version: " + configVersion.findOne() );

        System.out.println( "  shards:" );

        DBObject cmd = new BasicDBObject();
        cmd.put("listShards", 1);
        
        // cmd.put("key", new BasicDBObject("userId", 1));
        CommandResult result = db.command(cmd);
        @SuppressWarnings({ "rawtypes", "unchecked" })
        List<BasicDBObject> shards = (List<BasicDBObject>)result.get("shards");

        System.out.println( result );

        long count = 0L;

        for (BasicDBObject shard:shards) {
            String host = (String)shard.get("host");
            String[] parts = host.split("/");
            System.out.println("connecting to " + parts[1] );

            MongoClient ms = new MongoClient( new MongoClientURI("mongodb://"+parts[1]) );
            long c = ms.getDB( "twitter" ).getCollection( "tweets" ).count();
            System.out.println( "count: "+ c );
            count += c;
            ms.close();
        }

        System.out.println( "each shard total count: "+ count );

        System.out.println( "mongos total count: "+ m.getDB( "twitter" ).getCollection( "tweets" ).count() );

        // release resource
        m.close();
    }
}
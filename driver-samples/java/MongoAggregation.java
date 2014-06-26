/*
Requirements:
- Java
- Java Driver
- Mongod running

How to run this:
javac -cp .:mongo-java-driver-2.12.2.jar MongoAggregation.java && java -cp .:mongo-java-driver-2.12.2.jar: MongoAggregation

Sample output:
---
aggregate pipeline:
{ "$match" : { "symbol" : "DTEGn.DE" , "timestamp" : { "$exists" : true}}}
{ "$group" : { "_id" : { "Year" : { "$year" : "$timestamp"} , "Month" : { "$month" : "$timestamp"} , "Day" : { "$dayOfMonth" : "$timestamp"}}}}

output.results:
{ "_id" : { "Year" : 1970 , "Month" : 1 , "Day" : 1}}
{ "_id" : { "Year" : 2014 , "Month" : 6 , "Day" : 25}}
---
*/

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;
import com.mongodb.*;

public class MongoAggregation {

    public static void main(String[] args) throws Exception {
        MongoClient mongoClient = new MongoClient();
        DB db = mongoClient.getDB( "mydb" );
        String collection = "aggregate";
        DBCollection coll = db.getCollection(collection);

        //Do one query for each symbol
        DBObject match = new BasicDBObject("$match", new BasicDBObject("symbol", "DTEGn.DE").append("timestamp", new BasicDBObject("$exists", true)));

        DBObject groupfields =      new BasicDBObject("Year", new BasicDBObject("$year", "$timestamp"));
        groupfields.put("Month",    new BasicDBObject("$month", "$timestamp"));
        groupfields.put("Day",      new BasicDBObject("$dayOfMonth", "$timestamp"));
        DBObject group =        new BasicDBObject("$group", new BasicDBObject("_id", groupfields));

        List<DBObject> pipeline = Arrays.asList(match, group);
        System.out.println("aggregate pipeline:");
        System.out.println(match);
        System.out.println(group + "\n");
        AggregationOutput output = coll.aggregate(pipeline);

        System.out.println("output.results:");
        Iterable<DBObject> list = null;
        list = output.results();
        for (DBObject o : list) {
            System.out.println(o);
        }

    }
}
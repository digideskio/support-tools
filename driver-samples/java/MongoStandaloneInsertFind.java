/*
Requirements:
- Java

How to run this:
javac -cp .:mongo-2.10.1.jar MongoTest.java && java -cp .:mongo-2.10.1.jar: MongoTest

Sample output:
{ "_id" : { "$oid" : "517ed98b30041788595947cf"} , "name" : "MongoDB "}

*/

import com.mongodb.Mongo;
import com.mongodb.DBCollection;
import com.mongodb.BasicDBObject;
import com.mongodb.DB;

public class MongoStandaloneInsertFind {

    public static void main(String[] args) throws Exception {

        // connect to the local database server
        Mongo m = new Mongo();

        DB db = m.getDB( "test" );

        DBCollection coll = db.getCollection("test");

        // delete all the data from the 'test' collection
        coll.drop();

        // make a document and insert it
        BasicDBObject doc = new BasicDBObject();

        doc.put("name", "MongoDB ");

        coll.insert(doc);

        System.out.println( coll.findOne() );

        // release resources
        m.close();
    }
}
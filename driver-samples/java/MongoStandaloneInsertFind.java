/*
Requirements:
- Java

How to run this:
javac -cp .:mongo-java-driver-2.11.3.jar MongoStandaloneInsertFind.java && java -cp .:mongo-java-driver-2.11.3.jar: MongoStandaloneInsertFind

Sample output:
{ "_id" : { "$oid" : "517ed98b30041788595947cf"} , "name" : "MongoDB "}

*/

import com.mongodb.MongoClient;
import com.mongodb.DBCollection;
import com.mongodb.BasicDBObject;
import com.mongodb.DB;

public class MongoStandaloneInsertFind {

    public static void main(String[] args) throws Exception {

        // connect to the local database server
        MongoClient m = new MongoClient();

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
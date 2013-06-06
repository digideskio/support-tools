<?php
try {
  // open connection to MongoDB server
  $conn = new Mongo('localhost');

  // access database
  $db = $conn->test;

  // access collection
  $collection = $db->items;

  $array = $collection->findOne();

  if ( !empty($array) ) {
    die('test.items collection is not empty - not dropping');
  }

  // prepare a record
  date_default_timezone_set('Europe/Dublin');
  $date = new MongoDate(strtotime("2012-09-19 03:47:44"));

  $obj = array( "title" => "Calvin and Hobbes", "author" => "Bill Watterson", "published" => $date );

  $collection->insert($obj);

  print "1 document inserted\n";

  // execute query
  // retrieve all documents
  $cursor = $collection->find();

  // iterate through the result set
  // print each document
  echo $cursor->count() . " document(s) found.\n";
  foreach ($cursor as $obj) {
    echo 'Title: ' . $obj['title'] . "\n";
    echo 'Author: ' . $obj['author'] . "\n";
    echo 'Published: ' . date('Y-m-d H:i:s', $obj['published']->sec) . "\n";
  }

  $collection->drop();
  print "test.items dropped\n";

  // disconnect from server
  $conn->close();
} catch (MongoConnectionException $e) {
  die('Error connecting to MongoDB server');
} catch (MongoException $e) {
  die('Error: ' . $e->getMessage());
}
?>
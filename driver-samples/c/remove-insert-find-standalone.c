/*
Code taken from
example4.c from https://api.mongodb.org/c/0.96.2/deleting-document.html
example3.c from https://api.mongodb.org/c/0.96.2/inserting-document.html
example1.c from https://api.mongodb.org/c/0.96.2/finding-document.html

Run and output:
$ gcc -o remove-insert-find-standalone remove-insert-find-standalone.c $(pkg-config --cflags --libs libmongoc-1.0) && ./remove-insert-find-standalone

2014/06/17 12:08:51.0565: [83911]:    DEBUG:      cluster: Client initialized in direct mode.
{ "_id" : { "$oid" : "53a021c334181147c77e7341" }, "message" : "hello world" }
*/

#include <bson.h>
#include <mongoc.h>
#include <stdio.h>

int
main (int   argc,
      char *argv[])
{
    mongoc_client_t *client;
    mongoc_collection_t *collection;
    mongoc_cursor_t *cursor;
    bson_error_t error;
    bson_oid_t oid;
    bson_t *doc,
           *query;
    const bson_t *doc_query;
    char *str;

    mongoc_init ();

    client = mongoc_client_new ("mongodb://localhost:27017/");
    collection = mongoc_client_get_collection (client, "test", "test");

    doc = bson_new ();
    BSON_APPEND_UTF8 (doc, "message", "hello world");

    if (!mongoc_collection_remove (collection, MONGOC_REMOVE_SINGLE_REMOVE, doc, NULL, &error)) {
        printf ("Delete failed: %s\n", error.message);
    }

    bson_destroy (doc);

    doc = bson_new ();
    bson_oid_init (&oid, NULL);
    BSON_APPEND_OID (doc, "_id", &oid);
    BSON_APPEND_UTF8 (doc, "message", "hello world");

    if (!mongoc_collection_insert (collection, MONGOC_INSERT_NONE, doc, NULL, &error)) {
        printf ("%s\n", error.message);
    }

    bson_destroy (doc);

    doc_query = bson_new ();
    query = bson_new ();
    BSON_APPEND_UTF8 (query, "message", "hello world");
    cursor = mongoc_collection_find (collection, MONGOC_QUERY_NONE, 0, 0, 0, query, NULL, NULL);

    while (mongoc_cursor_next (cursor, &doc_query)) {
        str = bson_as_json (doc_query, NULL);
        printf ("%s\n", str);
        bson_free (str);
    }

    bson_destroy (query);
    mongoc_cursor_destroy (cursor);
    mongoc_collection_destroy (collection);
    mongoc_client_destroy (client);

    return 0;
}
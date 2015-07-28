import pymongo
import httplib
import json
import urllib

api_token="atF9STxts6nRX9vHA4BWF5GUmNQKZL"

users_store = pymongo.MongoClient('localhost', 27017).pushover.users;

def notify(title,message):
    total = 0;
    success = 0;

    conn = httplib.HTTPSConnection(host="api.pushover.net", port=443)
    cursor = users_store.find({})
    for user in cursor:
        total = total + 1;
        params = urllib.urlencode({'token':api_token,'user':user['key'],'message':message+" for " +user['_id'],'title':title})
        conn.request("POST", "/1/messages.json", params)
        content = conn.getresponse()
        json_doc = json.loads(content.read());
        if content.status == 200:
           if json_doc['status'] == 1:
               success = success + 1;
               print "Successfully notified " + user['_id'];
           else:
               print "Something went wrong while notifying " + user['_id'] + ": ", json_doc;
        else:
           print content.reason, content.status
           print "Something went wrong while notifying " + user['_id'] + ": ", json_doc;

    conn.close()
    return "Successfully notified " + str(success) + " out of " + str(total) + " users"


from bottle import redirect, response, request, route, run, template, url
import urllib
import random
import pymongo
import httplib
import json

sub_id="Wrapp-fgqsP47n1XjiqrQ"
api_token="atF9STxts6nRX9vHA4BWF5GUmNQKZL"

users_store = pymongo.MongoClient('localhost', 27017).pushover.users;

def full_url(path='/'):
    """
    Convert a specified path to full URL based on request data. This function
    uses the current request context information about the request URL to
    construct a full URL using specified path. In particular it uses
    ``bottle.request.urlparts`` to obtain information about scheme, hostname,
    and port (if any).

    Because it uses the request context, it cannot be called outside a request.

    :param path:    absolute path
    :returns:       full URL including scheme and hostname
    """
    parts = request.urlparts
    url = parts.scheme + '://' + parts.hostname
    if parts.port:
        url += ':' + str(parts.port)
    return url + path

@route('/hello')
def hello():
    return "Hello World!"

@route('/wrapp')
@route('/wrapp/push/subscribe')
def subscribe():
    rand = str(random.getrandbits(32));
    user = request.query.user or "anonymous";
    response.set_cookie("pushover_rand", rand);
    return template('''
<style type="text/css">
.pushover_button {
    box-sizing: border-box; background-color: #eee;
    background: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QAJQCeAPHNVUx7AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3wEPAh02ee0QVwAAACZpVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVAgb24gYSBNYWOV5F9bAAABqElEQVQ4y62TvUtbURjGf+fek2vQpMF2ED9QkfpR6VLaDoIEF0UKWQRBQ+yQP6GDU0Xw4y/obOgg6dDSJVS61MlBcXFQB6M1BsF+IES9NnrzcRy8xpvrBwH7bOflfc553+d5jsCF9tiRDwgBEaDXLi8B80AiGQ2Yzn7hIo8Cce5HOBkNfLo6aA7ydAVkgLjdez3BrS8rRbBJEmyU+AyBVVDE1i1SJ6psEmHvfOLktj0SjL/2snKQx8wpNg+LBJt0RjoN+j6bqOvN/ZotWAldtYK5gWpmV84YbPUw2ePlb7bI73+Kep+OLFONkGarXcK7l16+7+V57BW8qJMs7Ob5k4VQm4fVXzlyquyGiHRYBcC+WWQxnSP63AAgtn7O0FNJ9xOd0W+nbkF7pbsytXxOQw30N0t2MgX6Wzy8qtMJL5zy81jdsETaIXnjLL7trkLqGl+2svxI5/mwZt1l6ZJmJ6yEGqkYbveQOioQ2yiz7TbMa0DCWRnuMPBXaXzcsJx23YWEZmc7fJkqxdgzg8xZka/bFhVE2hSuKL+nMswko4GJ//KZxEO/8wVmfpjJTWeCTQAAAABJRU5ErkJggg==) 2px 2px no-repeat, linear-gradient(#FFF, #DEDEDE);
    border: 1px solid #CCC; border-radius: 3px; color: #333; display: inline-block;
    font: 11px/18px "Helvetica Neue",Arial,sans-serif; font-weight: bold;
    cursor: pointer; height: 22px; padding-left: 20px; padding-right: 5px;
    overflow: hidden; text-shadow: 0px 1px 0px rgba(255, 255, 255, 0.5);
    text-decoration: none; vertical-align: middle;
}
</style>

<a class="pushover_button" href="https://pushover.net/subscribe/{{sub_id}}?success={{success_url}}&failure={{failure_url}}">
  Subscribe With Pushover
</a>
''',
sub_id=sub_id, 
success_url=urllib.quote_plus(full_url("/wrapp/push/success")+"?rand="+rand+"&user="+user), 
failure_url=urllib.quote_plus(full_url("/wrapp/push/failure")));

@route('/wrapp/push/mock/<key>')
def mock(key):
    print "Token=" + key;
    print "Success=" + request.query.success;
    print "Failure=" + request.query.failure;
    redirect(request.query.failure)

@route('/wrapp/push/success')
def success():
    if (request.query.rand != request.get_cookie("pushover_rand")):
       return "BAD RAND TOKEN! (" + request.query.rand + " vs stored " + request.get_cookie("pushover_rand") + ")"

    user = request.query.user;

    if (request.query.pushover_user_key):
       users_store.update({'_id':user}, {"key" : request.query.pushover_user_key}, True);
       return "Successfully subscribed " + user + " with user key: " + request.query.pushover_user_key;
    elif (request.query.pushover_unsubscribed):
       users_store.remove({'_id':user});
       return "Successfully unsubscribed " + user;

    return "UNDEFINED SUCCESS!"

@route('/wrapp/push/failure')
def failure():
    return "Failed to subscribe!"

@route('/wrapp/notify')
def notify():
    message = request.query.message or "Default message";
    title = request.query.title or "Default title";

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

run(host='localhost', port=8080, debug=True)

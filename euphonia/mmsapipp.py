import bson
import bson.json_util
import pymongo
import urllib2
import time

try:
    mongo = pymongo.MongoClient()
    db_euphonia = mongo.euphonia
except pymongo.errors.PyMongoError as e:
    raise e


def queryMMSAPI(uri):
    # wait a spell so as not to piss off the MMS folk [too much]
    time.sleep(.5)

    auth_handler = urllib2.HTTPDigestAuthHandler()
    url = 'https://mms.mongodb.com/api/public/v1.0'
    # if uri is a full url, use it
    if uri.startswith(url):
        url = uri
    else:
        url = 'https://mms.mongodb.com/api/public/v1.0%s' % uri
    print(url)
    auth_handler.add_password(realm="MMS Public API",
                              uri=url,
                              # TODO move to config
                              user='xgen-sdash',
                              passwd='fc934098-b59c-40ad-85ad-8604a6cab8a1')
    opener = urllib2.build_opener(auth_handler)

    try:
        f = opener.open(url)
    except urllib2.HTTPError as e:
        return {'ok': False, 'payload': e}

    s = f.read()

    try:
        res = bson.json_util.loads(s)
    except Exception as e:
        return {'ok': False, 'payload': e}

    # cool story, the results may be paginated
    # if there's a 'next' link load that and append the result
    if 'results' in res:
        results = []
        results += res['results']
        links = res['links']
        for link in links:
            if link['rel'] == "next":
                res = queryMMSAPI(link['href'])
                if res['ok']:
                    results += res['payload']['results']
        res['results'] = results
    return {'ok': True, 'payload': res}


def getGroup(groupId):
    return queryMMSAPI('/groups/%s' % groupId)


def getGroupHosts(groupId):
    res = queryMMSAPI('/groups/%s/hosts' % groupId)
    if not res['ok']:
        return res
    return {'ok': True, 'payload': res['payload']['results']}


def getGroupHost(groupId, hostId):
    return queryMMSAPI('/groups/%s/hosts/%s' % (groupId, hostId))


def getGroupHostLastPing(groupId, hostId):
    return queryMMSAPI('/groups/%s/hosts/%s/lastPing' % (groupId, hostId))


def convertFieldIllegals(doc):
    keys = doc.keys()
    for key in keys:
        if key.find('.') > -1:
            newKey = key.replace('.', '\\p')
            doc[newKey] = doc.pop(key)
            key = newKey

        if key.startswith('$'):
            newKey = "\\$%s" % key[1:]
            doc[newKey] = doc.pop(key)
            key = newKey

        # coolio! now recursively scan values for keys
        val = doc[key]
        if isinstance(val, dict):
            doc[key] = convertFieldIllegals(val)
        elif isinstance(val, list):
            newVal = []
            for item in val:
                if isinstance(item, dict):
                    newVal.append(convertFieldIllegals(item))
                else:
                    newVal.append(item)
                # NOTE lack of list-check here means we only go one array deep
                # in performing the conversion
            doc[key] = newVal
    return doc


def saveGroup(groupId):
    saveGroupHighLevel(groupId)
    saveGroupLastPings(groupId)


def saveGroupHighLevel(groupId):
    res = getGroup(groupId)
    if not res['ok']:
        return res
    doc = res['payload']
    _id = doc['id']
    del doc['id']
    if 'links' in doc:
        del(doc['links'])

    try:
        db_euphonia.groups.update({'_id': _id}, {"$set": doc}, upsert=True)
    except pymongo.errors.PyMongoError as e:
        raise e


def saveGroupLastPings(groupId):
    res = getGroupHosts(groupId)
    if not res['ok']:
        return res
    hosts = res['payload']

    # used to identify pings fetched in this particular call to
    # getGroupLastPings; in essence, it defines what is a group
    tag = bson.ObjectId()

    for host in hosts:
        res = getGroupHostLastPing(groupId, host['id'])
        if not res['ok']:
            res['payload'] = {'ping': None}
        ping = res['payload']['ping']

        # find all fields containing '.' and convert to '\p'
        if ping is not None:
            ping = convertFieldIllegals(ping)

        doc = {'gid': groupId, 'hid': host['id'], 'tag': tag, 'ping': ping}
        saveLastPing(doc)


def saveLastPing(doc):
    try:
        db_euphonia.pings.insert(doc)
    except pymongo.errors.PyMongoError as e:
        raise e

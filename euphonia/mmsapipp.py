#!/usr/bin/env python
import argumentparserpp
import bson
import bson.json_util
import logging
import pymongo
import urllib2
import httplib
import time
import sys


class mmsapipp:
    def __init__(self, args):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

        # logLevel = self.args['log_level']
        logLevel = "DEBUG"
        logging.basicConfig()
        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logLevel)

        self.logger.debug(self.args)

        # Initialize dbs and collections
        try:
            self.mongo = pymongo.MongoClient(self.args['mongo_host'],
                                             self.args['mongo_port'])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e

        self.db_euphonia = self.mongo.euphonia

        # if query_who specified then we need to manually populate
        # the self.args['gid'] array
        if self.args.get('query_who') is not None:
            if self.args['query_who'] == "all":
                gid_curr = self.db_euphonia.mmsgroupreports.distinct('GroupId')
                self.args['gid'] = [gid for gid in gid_curr]
            elif self.args['query_who'] == "csOnly":
                gid_curr = self.db_euphonia.mmsgroupreports.find(
                    {'IsCsCustomer': True}).distinct('GroupId')
                self.args['gid'] = [gid for gid in gid_curr]

    def queryMMSAPI(self, uri):
        # wait a spell so as not to piss off the MMS folk [too much]
        time.sleep(self.args['timeout'])

        auth_handler = urllib2.HTTPDigestAuthHandler()
        url = 'https://mms.mongodb.com/api/public/v1.0'
        # if uri is a full url, use it
        if uri.startswith(url):
            url = uri
        else:
            url = 'https://mms.mongodb.com/api/public/v1.0%s' % uri
        self.logger.info(url)
        auth_handler.add_password(realm="MMS Public API",
                                  uri=url,
                                  # TODO move to config
                                  user=self.args['mmsapi_user'],
                                  passwd=self.args['mmsapi_token'])
        opener = urllib2.build_opener(auth_handler)

        try:
            f = opener.open(url)
        except (urllib2.HTTPError, urllib2.URLError) as e:
            return {'ok': False, 'payload': bson.json_util.loads(e.read())}
        except httplib.BadStatusLine as e:
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
                    res = self.queryMMSAPI(link['href'])
                    if res['ok']:
                        results += res['payload']['results']
            res['results'] = results
        return {'ok': True, 'payload': res}

    def getGroup(self, groupId):
        return self.queryMMSAPI('/groups/%s' % groupId)

    def getGroupHosts(self, groupId):
        res = self.queryMMSAPI('/groups/%s/hosts' % groupId)
        if not res['ok']:
            return res
        return {'ok': True, 'payload': res['payload']['results']}

    def getGroupHost(self, groupId, hostId):
        return self.queryMMSAPI('/groups/%s/hosts/%s' % (groupId, hostId))

    def getGroupHostLastPing(self, groupId, hostId):
        return self.queryMMSAPI('/groups/%s/hosts/%s/lastPing' %
                                (groupId, hostId))

    # TODO move this to a common lib?
    def convertFieldIllegals(self, doc):
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
                doc[key] = self.convertFieldIllegals(val)
            elif isinstance(val, list):
                newVal = []
                for item in val:
                    if isinstance(item, dict):
                        newVal.append(self.convertFieldIllegals(item))
                    else:
                        newVal.append(item)
                    # NOTE lack of list-check here means we only go one array
                    # deep in performing the conversion
                doc[key] = newVal
        return doc

    def run(self):
        self.logger.info("Querying %s groups", len(self.args['gid']))
        i = 0
        for gid in self.args['gid']:
            i += 1
            if (i + 1) % 10 == 0:
                self.logger.info("... %i (%.2f %%)", i+1,
                                 float(i+1)/len(self.args['gid']))
            if self.args['query_type'] == "all":
                res = self.saveGroup(gid)
                if not res['ok']:
                    self.logger.exception(res['payload'])
            elif self.args['query_type'] == "groupOnly":
                res = self.saveGroupHighLevel(gid)
                if not res['ok']:
                    self.logger.exception(res['payload'])
            elif self.args['query_type'] == "pingsOnly":
                res = self.saveGroupLastPings(gid)
                if not res['ok']:
                    self.logger.exception(res['payload'])
            else:
                self.logger.exception("Unknown query_type specified")
                sys.exit(3)

    def saveGroup(self, groupId):
        res = self.saveGroupHighLevel(groupId)
        if not res['ok']:
            self.logger.warning(res['payload'])
            return res
        doc = res['payload']
        groupName = doc['name']
        # pings don't include group name but we want to propagate them :(
        return self.saveGroupLastPings(groupId, groupName)

    def saveGroupHighLevel(self, groupId):
        res = self.getGroup(groupId)
        if not res['ok']:
            return res
        doc = res['payload']
        _id = doc['id']
        del doc['id']
        if 'links' in doc:
            del(doc['links'])

        try:
            doc = self.db_euphonia.groups.find_and_modify(query={'_id': _id},
                                                          update={"$set": doc},
                                                          upsert=True,
                                                          new=True)
        except pymongo.errors.PyMongoError as e:
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': doc}

    def saveGroupLastPings(self, groupId, groupName):
        res = self.getGroupHosts(groupId)
        if not res['ok']:
            return res
        hosts = res['payload']

        # used to identify pings fetched in this particular call to
        # getGroupLastPings; in essence, it defines what is a group
        tag = bson.ObjectId()

        for host in hosts:
            res = self.getGroupHostLastPing(groupId, host['id'])
            if not res['ok']:
                res['payload'] = {'ping': None}
            ping = res['payload']['ping']

            # find all fields containing '.' and convert to '\p'
            if ping is not None:
                ping = self.convertFieldIllegals(ping)

            doc = {'gid': groupId, 'name': groupName, 'hid': host['id'],
                   'tag': tag, 'doc': ping, 'hostInfo': host}
            self.saveLastPing(doc)
        return {'ok': True, 'payload': []}

    def saveLastPing(self, doc):
        try:
            self.db_euphonia.pings.insert(doc)
        except pymongo.errors.PyMongoError as e:
            return {'ok': False, 'payload': e}

if __name__ == "__main__":
    desc = "MMS API Plus Plus"
    parser = argumentparserpp.CliArgumentParser(description=desc)
    parser.add_config_argument(
        "--mongo-host", metavar="MONGO_HOST", default="localhost",
        help="specify the mongo hostname (default=localhost)"
    )
    parser.add_config_argument(
        "--mongo-port", metavar="MONGO_PORT", type=int, default=27017,
        help="specify the mongo port (default=27017)"
    )
    parser.add_config_argument(
        "--mmsapi-user", metavar="MMSAPI_USER",
        help="specify an MMS API user"
    )
    parser.add_config_argument(
        "--mmsapi-token", metavar="MMSAPI_TOKEN",
        help="specify an MMS API token"
    )
    parser.add_config_argument(
        "--timeout", metavar="SECONDS", default=0.5,
        help="specify the timeout between queries (default=0.5)"
    )
    parser.add_config_argument(
        "--query-type", metavar="QUERY_TYPE", default="all",
        choices=["all", "groupOnly", "pingsOnly"],
        help="specify the query type: all, groupOnly, pingsOnly (default=all)"
    )
    parser.add_config_argument(
        "--query-who", metavar="QUERY_WHO",
        choices=["all", "csOnly"],
        help="specify the category of MMS groups to query: all, csOnly; this "
             "overrides any gids specified"
    )
    parser.add_argument(
        "gid", nargs='*',
        help="<-- the MMS group id(s) to query"
    )
    args = parser.parse_args()

    if args.query_who is None and len(args.gid) == 0:
        print("Please specify MMS group id(s) to query")
        sys.exit(1)

    mms = mmsapipp(args)
    mms.run()
    sys.exit(0)

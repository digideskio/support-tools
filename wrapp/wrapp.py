#!/usr/bin/python
import argumentparserpp
import httplib
import json
import logging
import pymongo
import sys
import urllib


class Wrapp:
    """ Weekend responder app """
    def __init__(self, args, mongo=None):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

        logging.basicConfig(format='%(asctime)s - %(module)s - %(levelname)s -'
                                   ' %(message)s')
        self.logger = logging.getLogger("logger")

        if self.args.get('log_level') is not None:
            self.logger.setLevel(self.args['log_level'])

        if self.args.get('log') is not None:
            fh = logging.FileHandler(self.args['log'])
            self.logger.addHandler(fh)

        if mongo is None:
            mongo_uri = self.args.get('mongo_uri')
            if mongo_uri is None:
                e = "mongo_uri not specified"
                self.logger.exception(e)
                raise e

            try:
                self.mongo = pymongo.MongoClient(mongo_uri)
            except pymongo.errors.PyMongoError as e:
                self.logger.exception(e)
                raise e
        else:
            self.mongo = mongo

        # Initialize dbs and collections
        self.coll_users = self.mongo.karakuri.users

        self.pushbullet_host = self.args.get('pushbullet_host')
        self.pushbullet_port = self.args.get('pushbullet_port')
        if self.pushbullet_host is None or self.pushbullet_port is None:
            e = "Pushbullet host and port not specified"
            self.logger.exception(e)
            raise e

    def notify(self, title, message):
        total = 0
        success = 0

        conn = httplib.HTTPSConnection(host=self.pushbullet_host,
                                       port=self.pushbullet_port)
        match = {'pushbullet.access_token': {"$exists": True}}
        proj = {'_id': 0, 'pushbullet.access_token': 1, 'user': 1}
        try:
            cursor = self.coll_users.find(match, proj)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        for user in cursor:
            total += 1
            params = json.dumps({'type': 'note',
                                 'body': message,
                                 'title': title})
            headers = {'Access-Token': user['pushbullet']['access_token'],
                       'Content-Type': 'application/json'}
            conn.request("POST", "/v2/pushes", params, headers)
            content = conn.getresponse()
            json_doc = json.loads(content.read())
            if content.status == 200:
                if 'error' in json_doc:
                    self.logger.debug(json_doc)
                    self.logger.warning("Error notifying %s: %s", user['user'],
                                        json_doc['error']['message'])
                else:
                    self.logger.info("Successfully notified %s", user['user'])
                    success += 1
            else:
                self.logger.debug(json_doc)
                self.logger.warning("Error notifying %s: %s", user['user'],
                                    json_doc['error']['message'])

        conn.close()
        self.logger.info("Successfully notified %s out of %s users", success,
                         total)
        return {'ok': True, 'payload': {'success': success, 'total': total}}

if __name__ == "__main__":
    desc = "Weekend responder app"
    parser = argumentparserpp.CliArgumentParser(description=desc)
    parser.add_config_argument(
        "--mongo-uri", metavar="MONGO", default="mongodb://localhost:27017",
        help="specify the MongoDB connection URI "
             "(default=mongodb://localhost:27017)")
    parser.add_config_argument(
        "--pushbullet-host", metavar="PUSHBULLET_HOST",
        default="api.pushbullet.com",
        help="specify the Pushbullet host"
    )
    parser.add_config_argument(
        "--pushbullet-port", metavar="PUSHBULLET_PORT", default=443,
        help="specify the Pushbullet port"
    )
    parser.add_argument("title", help="title of push notification")
    parser.add_argument("message", help="message of push notification")
    args = parser.parse_args()

    w = Wrapp(args)
    w.notify(args.title, args.message)
    sys.exit(0)

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

        self.pushover_host = self.args.get('pushover_host')
        self.pushover_port = self.args.get('pushover_port')
        if self.pushover_host is None or self.pushover_port is None:
            e = "Pushover host and port not specified"
            self.logger.exception(e)
            raise e

        self.api_token = self.args.get('api_token')
        if self.api_token is None:
            e = "Pushover api_token not specified"
            self.logger.exception(e)
            raise e

    def notify(self, title, message):
        total = 0
        success = 0

        conn = httplib.HTTPSConnection(host=self.pushover_host,
                                       port=self.pushover_port)
        match = {'pushover.key': {"$exists": True}}
        proj = {'_id': 0, 'pushover.key': 1, 'user': 1}
        try:
            cursor = self.coll_users.find(match, proj)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        for user in cursor:
            total += 1
            params = urllib.urlencode({'token': self.api_token,
                                       'user': user['pushover']['key'],
                                       'message': message,
                                       'title': title})
            conn.request("POST", "/1/messages.json", params)
            content = conn.getresponse()
            json_doc = json.loads(content.read())
            if content.status == 200:
                if json_doc['status'] == 1:
                    self.logger.info("Successfully notified %s", user['user'])
                    success += 1
                else:
                    self.logger.warning("Error notifying %s: %s", user['user'],
                                        ','.join(json_doc['errors']))
                    self.logger.debug(json_doc)
            else:
                self.logger.warning("Error notifying %s: %s", user['user'],
                                    ','.join(json_doc['errors']))
                self.logger.debug(json_doc)

        conn.close()
        self.logger.info("Successfully notified %s out of %s users", success,
                         total)
        return {'ok': True, 'payload': {'success': success, 'total': total}}

if __name__ == "__main__":
    desc = "Weekend responder app"
    parser = argumentparserpp.CliArgumentParser(description=desc)
    parser.add_config_argument(
        "--api-token", metavar="API_TOKEN", help="specify a Pushover api token"
    )
    parser.add_config_argument(
        "--mongo-uri", metavar="MONGO", default="mongodb://localhost:27017",
        help="specify the MongoDB connection URI "
             "(default=mongodb://localhost:27017)")
    parser.add_config_argument(
        "--pushover-host", metavar="PUSHOVER_HOST", default="api.pushover.net",
        help="specify the Pushover host"
    )
    parser.add_config_argument(
        "--pushover-port", metavar="PUSHOVER_PORT", default=443,
        help="specify the Pushover port"
    )
    parser.add_argument("title", help="title of push notification")
    parser.add_argument("message", help="message of push notification")
    args = parser.parse_args()

    w = Wrapp(args)
    w.notify(args.title, args.message)
    sys.exit(0)

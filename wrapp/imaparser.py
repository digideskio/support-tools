#!/usr/bin/env python
import argumentparserpp
import email
import imaplib
import logging
import pymongo
import re
import sys
# import socket
import wrapp


class imaparser():
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

        # TODO redact passwords in a generic way
        self.logger.debug(self.args)

        if mongo is None:
            mongo_uri = self.args.get('mongo_uri')
            if mongo_uri is None:
                e = "mongo_uri not specified"
                self.logger.exception(e)
                raise Exception(e)

            try:
                self.mongo = pymongo.MongoClient(mongo_uri)
            except pymongo.errors.PyMongoError as e:
                self.logger.exception(e)
                raise e
        else:
            self.mongo = mongo

        # Initialize dbs and collections
        self.db_support = self.mongo.db_support
        self.coll_aps = self.db_support.aps

        self.imap_uri = self.args.get('imap_uri')
        self.imap_username = self.args.get('imap_username')
        self.imap_password = self.args.get('imap_password')

        if self.imap_uri is None or self.imap_username is None or\
                self.imap_password is None:
            e = "IMAP uri, username and password not specified"
            self.logger.exception(e)
            raise Exception(e)

        try:
            self.imap = imaplib.IMAP4_SSL(self.imap_uri)
        except Exception as e:
            self.logger.exception(e)
            raise e

        try:
            self.imap.login(self.imap_username, self.imap_password)
        except Exception as e:
            self.logger.exception(e)
            raise e

        self.wrapp = wrapp.Wrapp(self.args, self.mongo)

    def process_mailbox(self, mailbox):
        """ Process the imap mailbox named mailbox and return a list of matching
        mail objects """
        self.logger.debug("process_mailbox(%s)", mailbox)

        self.logger.debug("Selecting mailbox %s", mailbox)
        try:
            status, data = self.imap.select(mailbox)
        except Exception as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        if status == 'OK':
            pass
        else:
            e = "Failed to select mailbox %s" % mailbox
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        criterion = 'UNSEEN'
        self.logger.debug("Searching for %s", criterion)
        try:
            # the data is a space delimited array of message ids
            status, data = self.imap.search(None, criterion)
        except Exception as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        if status == 'OK':
            messageIds = data[0].split()
            self.logger.debug("%i email(s) found", len(messageIds))
        else:
            e = "Failed to search mailbox %s" % mailbox
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        # Return composite result of all message processing
        result = {'ok': True, 'payload': []}
        seenIds = []
        for messageId in messageIds:
            self.logger.debug("Fetching message %s", messageId)
            try:
                status, data = self.imap.fetch(messageId, '(RFC822)')
            except Exception as e:
                self.logger.exception(e)
                return {'ok': False, 'payload': e}

            if status != 'OK':
                e = "Error getting message %s" % messageId
                self.logger.exception(e)
                return {'ok': False, 'payload': e}

            # data is an array with a single tuple, so data[0] is just that
            # tuple; there first element in the tuple, data[0][0] looks like
            # '11 (RFC822 {6680}' and the second part starts with
            # "Delivered-To: so it's this second part we're turning into a
            # Message object
            msg = email.message_from_string(data[0][1])
            res = self.process_message(msg)
            # If the message was parsed successfully and matched what we were
            # looking for, save the messageId so we can mark it as Seen later
            # The payload is a Boolean that represents whether it was matched
            if res['ok'] is True and res['payload'] is True:
                seenIds.append(messageId)
            result['ok'] &= res['ok']
            result['payload'].append(res['payload'])

        # Mark matched messages as Seen so they don't show up again in our
        # preliminary search
        if len(seenIds) > 0:
            seenIdsString = ','.join(seenIds)
            self.logger.debug("Marking as seen: %s", seenIdsString)
            try:
                res = self.imap.store(seenIdsString, '+FLAGS', '\Seen')
            except Exception as e:
                self.logger.exception(e)
                return {'ok': False, 'payload': e}
        return result

    def process_message(self, msg):
        # self.logger.debug("process_message(%s)", msg)
        self.logger.debug("process_message(msg)")
        sender = email.utils.parseaddr(msg['From'])[1]
        subject = msg['Subject']
        date = msg['Date']
        # Note this is not the IMAP message number as used elsewhere, this is
        # presumably unique. We'll use this to make sure we don't send out
        # repeat alerts
        messageId = msg['Message-ID']

        # if is_multipart() is True, then payload is a list of Message
        # objects of which we want the plain one
        if msg.is_multipart():
            for part in msg.get_payload():
                charset = part.get_content_charset()
                if charset is None:
                    # can't decode if we don't know the encoding :/
                    text = part.get_payload(decode=True)
                else:
                    # but if we do we definitely want to convert this to utf8
                    text = unicode(part.
                                   get_payload(decode=True), str(charset), "ignore").\
                        encode('utf8', 'replace')
        # otherwise it's a string
        else:
            text = unicode(msg.
                           get_payload(decode=True), msg.get_content_charset(), 'ignore').\
                encode('utf8', 'replace')

        self.logger.debug("sender: %s", sender)
        self.logger.debug("subject: %s", subject)
        self.logger.debug("date: %s", date)
        self.logger.debug("messageId: %s", messageId)
        # self.logger.debug("text: %s", text)

        # Is this an Alphapage?
        if sender.lower() == "mongo@beanmix.com" and\
                re.search(r'Alphapage message', subject):
            res = self.process_ap(text)
        # Did a CS customer file an issue in a non-CS project?
        elif sender.lower() == "info@10gen.com" and\
                re.search(r'Issues filed by CS customers in non-CS projects',
                          subject):
            res = self.process_misfiled(text)
        else:
            res = {'ok': True, 'payload': False}
        return res

    def process_ap(self, text):
        """ Parse out the various fields expected of an Alphapage message """
        # self.logger.debug("process_ap(%s)", text)
        self.logger.debug("process_ap(text)")
        text = text.replace('\r', '|').replace('\n', '|').replace('`', '')

        # this was a pain in the ass
        common_reg = '\|?%s:([^|]*)\|'
        fields = ['Existing Client', 'Caller', 'Company', 'Location', 'Phone',
                  'JIRA #', 'Priority', 'Work begun', 'Message']
        ap_doc = {}
        for field in fields:
            m = re.search(common_reg % field, text)
            if m is None:
                ap_doc[field.lower()] = None
            else:
                ap_doc[field.lower()] = m.group(1).strip()

        self.logger.info("Found Alphapage message!")
        self.logger.info(ap_doc)
        self.wrapp.notify("Alphapage message: " + ap_doc['caller'] + " from " +
                          ap_doc['company'], text)
        return {'ok': True, 'payload': True}

    def process_misfiled(self, text):
        self.logger.debug("process_misfiled(%s)", text)
        misfiled_doc = {}

        m = re.search('https://jira.mongodb.org/browse/(\S+) - (.*)\r', text)
        if m is None:
            misfiled_doc['key'] = None
            misfiled_doc['summary'] = None
        else:
            misfiled_doc['key'] = m.group(1)
            misfiled_doc['summary'] = m.group(2)

        m = re.search('Reporter: (.*) from (.*) \((.*)\)', text)
        if m is None:
            misfiled_doc['reporter'] = None
            misfiled_doc['group'] = None
        else:
            misfiled_doc['reporter'] = m.group(1)
            misfiled_doc['group'] = m.group(2)

        m = re.search('created on (.*)\r', text)
        if m is None:
            misfiled_doc['created'] = None
        else:
            misfiled_doc['created'] = m.group(1)

        self.logger.info("Found misfiled ticket!")
        self.logger.info(misfiled_doc)
        self.wrapp.notify("Misfiled ticket: " + misfiled_doc['reporter'] +
                          " from " + misfiled_doc['group'], text)
        return {'ok': True, 'payload': True}

if __name__ == "__main__":
    desc = "An IMAP parser for APs"
    parser = argumentparserpp.CliArgumentParser(description=desc)
    parser.add_config_argument(
        "--mongo-uri", metavar="MONGO", default="mongodb://localhost:27017",
        help="specify the MongoDB connection URI "
             "(default=mongodb://localhost:27017)")
    parser.add_config_argument(
        "--imap-uri", metavar="IMAP_URI", default="imap.google.com",
        help="specify the IMAP connection URI "
             "(default=imap.google.com)")
    parser.add_config_argument(
        "--imap-username", metavar="IMAP_USERNAME",
        help="specify the IMAP username"
    )
    parser.add_config_argument(
        "--imap-password", metavar="IMAP_PASSWORD",
        help="specify the IMAP password"
    )
    # that below is in wrapp and temporary
    parser.add_config_argument(
        "--api-token", metavar="API_TOKEN", help="specify a Pushover api token"
    )
    parser.add_config_argument(
        "--pushover-host", metavar="PUSHOVER_HOST", default="api.pushover.net",
        help="specify the Pushover host"
    )
    parser.add_config_argument(
        "--pushover-port", metavar="PUSHOVER_PORT", default=443,
        help="specify the Pushover port"
    )
    args = parser.parse_args()

    i = imaparser(args)
    i.process_mailbox("inbox")
    i.imap.close()
    i.imap.logout()
    sys.exit(0)

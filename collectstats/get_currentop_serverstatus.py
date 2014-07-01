#!/usr/bin/env python2

"""
Small script to periodically sample db.serverStatus() and db.currentOp() from a running MongoDB instance, and store them into another MongoDB instance.

It will save it's output to the database "get_currentop_serverstatus" in a collection named "<host><port>".

Disclaimer: This script is released for use "AS IS" without any warranties of any kind, including, but not limited to their installation, use, or performance. We disclaim any and all warranties, either express or implied, including but not limited to any warranty of noninfringement, merchantability, and/ or fitness for a particular purpose. We do not warrant that the technology will meet your requirements, that the operation thereof will be uninterrupted or error-free, or that any errors will be corrected.

Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and we are not responsible for any damage or data loss incurred with their use.

You are responsible for reviewing and testing any scripts you run thoroughly before use in any non-testing environment.

Author: Victor Hooi (victor.hooi@mongodb.com)
Date: 2014-06-27
"""

import argparse
from datetime import datetime
import logging
from time import sleep
from pymongo import MongoClient, errors
from urlparse import urlparse


def get_server_status(db):
    return db.command('serverStatus')

def get_current_op(db):
    # return client.admin["$cmd.sys.inprog"].find_one()
    return db.current_op()

def setup_argparse():
    parser = argparse.ArgumentParser(description='Sample the output of db.currentOp() and db.serverStatus() at regular intervals.')
    parser.add_argument('--targetmongodb', default='mongodb://localhost:27017/', help='The target MongoDb to sample from (MongoDB URI format). Defaults to "mongodb://localhost:27017/"')
    parser.add_argument('--sampleinterval', default=0.1, nargs='?', help='The sampling interval to use. Defaults to 100 milliseconds.', type=float)
    parser.add_argument('--outputmongodb', default='mongodb://localhost:27017/', help='The output MongoDb to write results to (MongoDB URI format). Defaults to "mongodb://localhost:27017/"')
    parser.add_argument('--logfile', default='get_currentop_serverstatus.log', nargs='?', help='The output file to write results to. Defaults to "get_currentop_serverstatus.log".')
    parser.add_argument('--debug', action='store_true', help='Set the logging level to DEBUG.')
    return parser.parse_args()

def setup_logging(logfile, debug):
    logger = logging.getLogger('get_currentop_serverstatus')
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    fh = logging.FileHandler(logfile)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fh)


# Since serverStatus and currentOp can return docs with fields that contain . and/or $,
# these need to be sanitized before they can be stored in a collection.
def sanitize_doc(son):
	if not isinstance(son, dict):
		return son
	for (key, value) in son.items():
		if isinstance(value, dict):
			newvalue = sanitize_doc(value)
		elif isinstance(value, list):
			l = []
			for i in value:
				l.append(sanitize_doc(i))
			newvalue = l
		else:
			newvalue = value
		if "." in key or "$" in key:
			son.pop(key)
			son[key.replace(".", "_DOT_").replace("$", "_DOLLAR_")] = newvalue
		else:
			son[key] = newvalue
	return son


if __name__ == "__main__":
    args = setup_argparse()
    setup_logging(args.logfile, args.debug)
    logger = logging.getLogger('get_currentop_serverstatus')
    output_collection_name = urlparse(args.outputmongodb).netloc.replace(':', '')

    try:
        target_client = MongoClient(args.targetmongodb)
        target_db = target_client.test
        logger.info('Collecting samples from mongodb://{}:{}.'.format(target_client.host, target_client.port))
    except errors.ConnectionFailure as e:
        logger.error('Error connecting to {} - {}'.format(args.targetmongodb, e))
        exit()

    try:
        output_client = MongoClient(args.outputmongodb)
        output_db = output_client.get_currentop_serverstatus
        logger.info('Outputting results to mongodb://{}:{} using database {}.'.format(output_client.host, output_client.port, output_db.name))
    except errors.ConnectionFailure as e:
        logger.error('Error connecting to {} - {}'.format(args.outputmongodb, e))
        exit()

    while True:
        output = {'client_ts': datetime.now(), 'server_status': get_server_status(target_db), 'current_op': get_current_op(target_db)}
        logger.debug(output)
        output_db[output_collection_name].insert(sanitize_doc(output))
        sleep(args.sampleinterval)

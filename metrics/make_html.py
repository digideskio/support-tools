#!/usr/bin/python

import pymongo
from datetime import datetime, timedelta
import os
from ConfigParser import RawConfigParser

config = RawConfigParser()
config_paths = ['jira.cfg', '../jira.cfg']
config.read([os.path.join(os.getcwd(), path) for path in config_paths])

conn = pymongo.MongoClient(config.get('Mongo', 'uri'))
metrics = conn.metrics

def MakeHTML():
    cursor = metrics.catalog.find({'type': 'weekly'})
    cursor.sort([('date', pymongo.DESCENDING)])

    yield('<title>Support Metrics Index</title>')
    yield('<h2>Support Metrics Index</h2>')
    yield('TODO: make this page less of a Spartan eyesore.')
    yield('<p>Metrics for week ending:')
    yield('<ul>')

    for row in cursor:
        yesterday = row['date'] - timedelta(days=1)
        yield('<li><a href="%s">%s</a>' % (
            row['url'], yesterday.strftime('%Y-%m-%d %A')))
    yield('</ul>')

def Main():
    directory = os.path.join(os.getcwd(), 'html')
    if not os.path.exists(directory): os.mkdir(directory)
    fh = open(os.path.join(directory, 'index.html'), mode="w")
    for x in MakeHTML():
        fh.write(x)
    fh.close()

Main()


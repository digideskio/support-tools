import grouptestdocument
import logging
import ping
import pymongo


class GroupPing(grouptestdocument.GroupTestDocument):
    def __init__(self, groupId, tag=None, *args, **kwargs):
        self.tag = tag
        self.mongo = kwargs['mongo']

        # Individual ping documents
        self.pings = {}
        # If tag not specified get the most recent tag of the group
        if self.tag is None:
            try:
                match = {'gid': groupId}
                proj = {'_id': 0, 'tag': 1}
                curr_pings = self.mongo.euphonia.pings.find(match, proj).\
                    sort("tag", -1).limit(1)
            except pymongo.errors.PyMongoError as e:
                raise e

            if curr_pings.count() > 0:
                self.tag = curr_pings[0]['tag']

        if self.tag is not None:
            try:
                # Get all pings with this tag
                match = {'tag': self.tag}
                curr_pings = self.mongo.euphonia.pings.find(match)
            except pymongo.errors.PyMongoError as e:
                raise e

            for p in curr_pings:
                self.pings[p['_id']] = ping.Ping(p)

        from groupping_tests import GroupPingTests
        grouptestdocument.GroupTestDocument.__init__(
            self, groupId=groupId,
            mongo=self.mongo,
            src='pings',
            testsLibrary=GroupPingTests)

    def groupName(self):
        if len(self.pings) > 0:
            return self.pings.values()[0].doc['name']
        return self.group.get('name')

    def isCsCustomer(self):
        if self.company is not None:
            return self.company.get('has_cs')
        return False

    def forEachHost(self, test, *args, **kwargs):
        ok = True
        res = True
        ids = []
        for pid in self.pings:
            testRes = test(self.pings[pid], *args, **kwargs)
            if testRes is None:
                ok = False
                self.logger.warning('Test returned bad document format')
            elif not testRes:
                res = False
                ids.append(pid)
        return {'ok': ok, 'payload': {'pass': res, 'ids': ids}}

    def forEachPrimary(self, test, *args, **kwargs):
        ok = True
        res = True
        ids = []
        for pid in self.pings:
            if self.pings[pid].isPrimary():
                testRes = test(self.pings[pid], *args, **kwargs)
                if testRes is None:
                    ok = False
                    self.logger.warning('Test returned bad document format')
                elif not testRes:
                    res = False
                    ids.append(pid)
        return {'ok': ok, 'payload': {'pass': res, 'ids': ids}}

    def next(self):
        """ Return the GroupPing after this one """
        try:
            match = {'gid': self.groupId(), 'tag': {"$gt": self.tag}}
            proj = {'tag': 1, '_id': 0}
            curr_pings = self.mongo.euphonia.pings.find(match, proj).\
                sort("tag", -1).limit(1)
        except pymongo.errors.PyMongoError as e:
            raise e

        if curr_pings.count():
            tag = curr_pings[0]['tag']
            return GroupPing(self.groupId(), tag, mongo=self.mongo,
                             src=self.src)
        else:
            return None

    def prev(self):
        """ Return the GroupPing before this one """
        try:
            match = {'gid': self.groupId(), 'tag': {"$lt": self.tag}}
            proj = {'tag': 1, '_id': 0}
            curr_pings = self.mongo.euphonia.pings.find(match, proj).\
                sort("tag", 1).limit(1)
        except pymongo.errors.PyMongoError as e:
            raise e
        if curr_pings.count():
            tag = curr_pings[0]['tag']
            return GroupPing(self.groupId(), tag, mongo=self.mongo,
                             src=self.src)
        else:
            return None

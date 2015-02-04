import grouptestdocument
import ping
import pymongo


class GroupPing(grouptestdocument.GroupTestDocument):
    def __init__(self, groupId, tag=None, *args, **kwargs):
        self.tag = tag
        from groupping_tests import GroupPingTests
        grouptestdocument.GroupTestDocument.__init__(
            self, groupId=groupId,
            mongo=kwargs['mongo'],
            src='pings',
            testsLibrary=GroupPingTests)

        # Individual host ping documents
        self.pings = {}
        # If tag not specified get the most recent tag of the group
        if self.tag is None:
            try:
                match = {'gid': self.groupId()}
                proj = {'_id': 0, 'tag': 1}
                curr_pings = self.mongo.euphonia.pings.find(match, proj).\
                    sort("tag", -1).limit(1)
            except pymongo.errors.PyMongoError as e:
                raise e

            self.tag = curr_pings[0]['tag']

        try:
            # Get all host pings with this tag
            match = {'tag': self.tag}
            curr_pings = self.mongo.euphonia.pings.find(match)
        except pymongo.errors.PyMongoError as e:
            raise e

        for p in curr_pings:
            self.pings[p['_id']] = ping.Ping(p)

    def isCsCustomer(self):
        if self.company is not None:
            return self.company['has_cs']
        return False

    def forEachHost(self, test, *args, **kwargs):
        res = True
        ids = []
        for pid in self.pings:
            if not test(self.pings[pid], *args, **kwargs):
                res = False
                ids.append(pid)
        return {'pass': res, 'ids': ids}

    def forEachPrimary(self, test, *args, **kwargs):
        res = True
        ids = []
        for pid in self.pings:
            if self.pings[pid].isPrimary():
                if not test(self.pings[pid], *args, **kwargs):
                    res = False
                    ids.append(pid)
        return {'pass': res, 'ids': ids}

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
            return GroupPing(self.groupId(), tag, mongo=self.mongo, src=self.src)
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
            return GroupPing(self.groupId(), tag, mongo=self.mongo, src=self.src)
        else:
            return None

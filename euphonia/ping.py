import logging


class Ping:
    """ A host's last ping document """
    def __init__(self, doc):
        self.doc = doc

    def getPingSubdoc(self, projection):
        # get the subdocuments based on the projection
        # similar to how projection works in the find command

        subdoc = self.doc
        subdocTree = projection.split(".")
        subdocTree.insert(0, "doc")
        try:
            # iterate through the subdocuments
            for key in subdocTree:
                subdoc = subdoc[key]
        except Exception:
            logging.getLogger("logger") \
                .warning("document does not have the field " + projection)
            return None
        return subdoc

    def getBuildInfo(self):
        return self.getPingSubdoc('buildInfo')

    def getCmdLineOpts(self):
        return self.getPingSubdoc('cmdLineOpts')

    def getConfigCollections(self):
        return self.getPingSubdoc('configCollections')

    def getConfigDatabases(self):
        return self.getPingSubdoc('configDatabases')

    def getConfigLockpings(self):
        return self.getPingSubdoc('configLockpings')

    def getConfigSettings(self):
        return self.getPingSubdoc('configSettings')

    def getConfigShards(self):
        return self.getPingSubdoc('configShards')

    def getConnPoolStats(self):
        return self.getPingSubdoc('connPoolStats')

    def getDbProfileData(self):
        return self.getPingSubdoc('dbProfileData')

    def getDbProfiling(self):
        return self.getPingSubdoc('dbProfiling')

    def getDuplicateHost(self):
        return self.getPingSubdoc('duplicateHost')

    def getGetParameterAll(self):
        return self.getPingSubdoc('getParameterAll')

    def getHost(self):
        return self.getPingSubdoc('host')

    def getHostInfo(self):
        return self.getPingSubdoc('hostInfo')

    def getHostIpAddr(self):
        return self.getPingSubdoc('hostIpAddr')

    def getIsMaster(self):
        return self.getPingSubdoc('isMaster')

    def getIsSelf(self):
        return self.getPingSubdoc('isSelf')

    def getLocalSystemReplSet(self):
        return self.getPingSubdoc('localSystemReplSet')

    def getLocks(self):
        return self.getPingSubdoc('locks')

    def getMongoses(self):
        return self.getPingSubdoc('mongoses')

    def getNetstat(self):
        return self.getPingSubdoc('netstat')

    def getOplog(self):
        return self.getPingSubdoc('oplog')

    def getPort(self):
        return self.getPingSubdoc('port')

    def getReplStatus(self):
        return self.getPingSubdoc('replStatus')

    def getServerStatus(self):
        return self.getPingSubdoc('serverStatus')

    def getServerStatusExecTimeMS(self):
        return self.getPingSubdoc('serverStatusExecTimeMs')

    def getShards(self):
        return self.getPingSubdoc('shards')

    def getStartupWarnings(self):
        return self.getPingSubdoc('startupWarnings')

    def getArgv(self):
        return self.getPingSubDoc('cmdLineOpts.argv')
    
    def getCurrentConnections(self):
        return self.getPingSubDoc('serverStatus.connections.current')

    def getMappedMemory(self):
        return self.getPingSubDoc('serverStatus.mem.mapped')

    def getMappedWithJournalMemory(self):
        return self.getPingSubDoc('serverStatus.mem.mappedWithJournal')

    def getVirtualMemory(self):
        return self.getPingSubDoc('serverStatus.mem.virtual')

    def getHostId(self):
        return self.doc['hid']

    def isPrimary(self):
        doc = self.getIsMaster()
        if doc is not None and 'ismaster' in doc:
            return doc['ismaster'] and not self.isConfig() and\
                not self.isMongos() and not self.isStandalone()
        return None

    def isConfig(self):
        doc = self.getCmdLineOpts()
        if doc is not None and 'parsed' in doc:
            parsed = doc['parsed']
            if ('configsvr' in parsed and parsed['configsvr'] is True) or\
                    ('sharding' in parsed and
                     'clusterRole' in parsed['sharding'] and
                        parsed['sharding']['clusterRole'] == "configsvr"):
                return True
        return False

    def isMongos(self):
        doc = self.getCmdLineOpts()
        if doc is not None and 'parsed' in doc:
            parsed = doc['parsed']
            if 'configdb' in parsed or\
                ('sharding' in parsed and
                    'configDB' in parsed['sharding']):
                return True
        return False

    def isStandalone(self):
        return self.getLocalSystemReplSet() is None

    def replsetName(self):
        doc = self.getLocalSystemReplSet()
        if doc is not None:
            return doc['_id']
        return None

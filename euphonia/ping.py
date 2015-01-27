class Ping:
    """ A host's last ping document """
    def __init__(self, doc):
        self.doc = doc

    def getPingSubdoc(self, subdocName):
        if self.doc['ping'] is not None and subdocName in self.doc['ping']:
            return self.doc['ping'][subdocName]
        return None

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

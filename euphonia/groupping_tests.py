import re
import datetime

from collections import defaultdict


class GroupPingTests:
    # Note the convention: If it passes the test, then it returns True.
    # Otherwise, it returns false
    @staticmethod
    def isNotVersion(host, regex):
        doc = host.getServerStatus()
        if doc is not None and 'version' in doc:
            if re.match(regex, doc['version']):
                return False
        return True

    @classmethod
    def testVisibleDelayedSecondaries(cls, groupPing):
        def hiddenAndPriority0(host):
            members = host.getReplNodeMembers()
            if not (type(members) is list):
                return None

            passed = True
            for member in members:
                if "priority" in member \
                        and "hidden" in member \
                        and "slaveDelay" in member:

                    if member["slaveDelay"] == 0:
                        continue
                    if member["priority"] != 0 or member["hidden"] is False:
                        passed = False
                    elif passed is True:
                        # data is considered incomplete
                        # only if we haven't failed
                        passed = None
            return passed
        return groupPing.forEachPrimary(hiddenAndPriority0)

    # This is a test for an even number of voting members in a replica set
    @classmethod
    def testEvenVotingNumberReplicaSets(cls, groupPing):
        def hasOddVotes(host):
            votes = 0
            doc = host.getLocalSystemReplSet()
            if doc is not None and 'members' in doc:
                for member in doc['members']:
                    if 'votes' in member:
                        votes += member['votes']
                    else:
                        votes += 1
            return votes % 2 != 0
        return groupPing.forEachPrimary(hasOddVotes)

    # This is a test for NUMA-related warnings on startup
    @classmethod
    def testNumaStartupWarning(cls, groupPing):
        def hasNoNumaWarning(host):
            doc = host.getStartupWarnings()
            if doc is not None and 'log' in doc:
                # Criteria used for MMS group reports:
                # https://github.com/10gen/mms/blob/master/operations/reports/mms_group_report.py#L149
                if re.search('numa', '\\n'.join(doc['log']), re.IGNORECASE):
                    return False
            return True
        return groupPing.forEachHost(hasNoNumaWarning)

    # This is a test for warnings on startup. It is inclusive to the NUMA and
    # Limits tests
    @classmethod
    def testStartupWarning(cls, groupPing):
        def hasNoStartupWarning(host):
            doc = host.getStartupWarnings()
            if doc is not None and 'log' in doc:
                if len(doc['log']) != 0:
                    return False
            return True
        return groupPing.forEachHost(hasNoStartupWarning)

    @classmethod
    def testNumReplicaSetWithMoreThanOneArbiter(cls, groupPing):
        def hasLTE1Arbiter(host):
            narbiter = 0
            doc = host.getLocalSystemReplSet()
            if doc is not None and 'members' in doc:
                for member in doc['members']:
                    if 'arbiterOnly' in member and\
                            member['arbiterOnly'] is True:
                        narbiter += 1
            return narbiter <= 1
        return groupPing.forEachPrimary(hasLTE1Arbiter)

    @classmethod
    def testNumHostWithVotesMoreThanOne(cls, groupPing):
        def hasLTE1Vote(host):
            res = True
            doc = host.getLocalSystemReplSet()
            if doc is not None and 'members' in doc:
                for member in doc['members']:
                    if 'votes' in member and member['votes'] > 1:
                        res = False
            return res
        return groupPing.forEachPrimary(hasLTE1Vote)

    @classmethod
    def testMongosNoAutoSplit(cls, groupPing):
        def hasNoAutoSplit(host):
            argv = host.getArgv()
            if argv:
                return "noAutoSplit" in argv
            return None
        return groupPing.forEachHost(hasNoAutoSplit)

    # tests if the replset version increased by more than maxElectionsPerDay per day
    @classmethod
    def testReplSetHighVersionNumber(cls, groupPing):
        maxElectionsPerDay = 48

        # dictionary of replset versions by hid
        versionDict = defaultdict(list)
        # dictionary of query times
        queryTimestampDict = defaultdict(list)
        # dictionary of ping IDs
        idsDict = defaultdict(list)

        def buildCurrentState(host):
            pingTime = host.getPingTime()
            replVersion = host.getReplSetVersion()
            hid = host.getHostId()

            if not (pingTime and replVersion and hid):
                return None

            versionDict[hid].append(replVersion)
            queryTimestampDict[hid].append(pingTime)
            idsDict[hid].append(host.getId())

        while groupPing:
            groupPing.forEachHost(buildCurrentState)
            groupPing = groupPing.prev()

        res = True
        ids = []

        for hid in versionDict.keys():
            versions = versionDict[hid]
            ts = queryTimestampDict[hid]
            pids = idsDict[hid]

            if len(versions) < 1:
                # not enough datapoints for this node
                continue
            elif len(versions) < 2:
                # only one datapoint
                if versions[0] > maxElectionsPerDay * 7:
                    ids.append(pids[0])
                    res = False
            else:
                # at least 2 data points:
                for i in range(1, len(versions)):
                    dt = (ts[i-1] - ts[i]).total_seconds() / 86400
                    dv = (versions[i-1] - versions[i])

                    if dt > dv * maxElectionsPerDay:
                        ids.append(pids[i-1])
                        ids.append(pids[i])
                        res = False

        return {'pass':  res, 'ids': list(set(ids))}

    # This is a test for ulimit-related warnings on startup
    @classmethod
    def testLimitsStartupWarning(cls, groupPing):
        def hasNoLimitsWarning(host):
            doc = host.getStartupWarnings()
            if doc is not None and 'log' in doc:
                # Criteria used for MMS group reports:
                # https://github.com/10gen/mms/blob/master/operations/reports/mms_group_report.py#L152
                if re.search('rlimits', '\\n'.join(doc['log']), re.IGNORECASE):
                    return False
            return True
        return groupPing.forEachHost(hasNoLimitsWarning)

    # This is a test for MongoDB < 2.0.2 which contains a data integrity
    # related bug re open sockets on replSetStepDown: SERVER-4405
    @classmethod
    def testMongo20ReplSetStepDown(cls, groupPing):
        # <= 2.0.1
        regex = '^2.0.[01](-|$)'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.2.0 which contains idempotency and
    # replication bugs:
    # https://wiki.mongodb.com/display/cs/Idempotency+and+MongoDB+2.2+replication
    @classmethod
    def testMongo22Idempotency(cls, groupPing):
        # 2.2.0
        regex = '^2.2.0'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.x (x<5) which contains a security related
    # vulnerability wherein authentication takes a database lock it shouldn't:
    # SERVER-9983
    @classmethod
    def testMongo24AuthDbLock(cls, groupPing):
        # <= 2.4.4
        regex = '^2.4.[0-4](-|$)'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.x (x<8) which contains a dbhash cache bug
    # https://wiki.mongodb.com/display/cs/2.4.7+-+SERVER-11421+-+Cached+dbhash+for+the+config.chunks+collection+not+updated
    @classmethod
    def testMongo24DbhashCache(cls, groupPing):
        # <= 2.4.7
        regex = '^2.4.[0-7](-|$)'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.x (x<5) which contains a security related
    # vulnerability that could allow a remotely triggered seg fault in the JS
    # engine: SERVER-9878
    @classmethod
    def testMongo24JSRemoteSegfault(cls, groupPing):
        # <= 2.4.4
        regex = '^2.4.[0-4](-|$)'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.0 which contains an initial sync bug
    # SERVER-9087
    @classmethod
    def testMongo24InitialSync(cls, groupPing):
        # 2.4.0
        regex = '^2.4.0'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.0 which contains a data integreity related
    # bug re secondary indexes: SERVER-9087
    @classmethod
    def testMongo24SecondaryIndexes(cls, groupPing):
        # 2.4.0
        regex = '^2.4.0'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.6.0 which contains a security related
    # vulnerability re user credentials: SERVER-13644
    @classmethod
    def testMongo26Credentials(cls, groupPing):
        # 2.6.0
        regex = '^2.6.0'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.6.0 and 2.6.1 which contain an x.509
    # security related vulnerability: SERVER-13753
    @classmethod
    def testMongo26X509Auth(cls, groupPing):
        # <= 2.6.1
        regex = '^2.6.[01](-|$)'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB <= 2.2.3, 2.4.1 which contain a security
    # related vulnerability re JS function conflics in the mongo shell:
    # SERVER-9131
    # NOTE SERVER-9131 is in Planning Bucket A, is it even fair to limit to
    # these releases?
    @classmethod
    def testMongoJSShellConflicts(cls, groupPing):
        # <= 2.2.3, <= 2.4.1
        regex = '(^2.2.[0-3](-|$))|(^2.4.[01](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB < 2.2.6 and < 2.4.6 which contain a data
    # integrity related bug re large chunk migratoins: SERVER-10478
    @classmethod
    def testMongoLargeChunkMigrations(cls, groupPing):
        if groupPing.group['shardCount'] == 0:
            return {'ok': True, 'payload': {'pass': True}}
        # <= 2.2.5, <= 2.4.5
        regex = '(^2.2.[0-5](-|$))|(^2.4.[0-5](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB <= 1.8.4 and <= 2.0.1 which contain a data
    # integrity related bug re missing documents on secondaries: SERVER-3956,
    # SERVER-4270
    # NOTE These SERVER tickets have different fix versions so we'll take the
    # later one to be more conservative
    @classmethod
    def testMongoSecondaryMissingDocs(cls, groupPing):
        # <= 1.8.4, <= 2.0.1
        regex = '(^1.8.[0-4](-|$))|(^2.0.[01](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB <= 2.0.8, 2.2.3, 2.4.1 which contain a
    # security related vulnerability re SpiderMonkey's JS nativeHelper
    # function: SERVER-9124
    @classmethod
    def testMongoSMNativeHelper(cls, groupPing):
        # <= 2.0.8, <= 2.2.3, <= 2.4.1
        regex = '(^2.0.[0-8](-|$))|(^2.2.[0-3](-|$))|(^2.4.[01](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.[0-10] and 2.6.[0-3] which contain a data
    # integrity related bug re text-indexed fields: SERVER-14738
    @classmethod
    def testMongoTextIndexedFields(cls, groupPing):
        # <= 2.4.10, <= 2.6.3
        regex = '(^2.4.([0-9]|10)(-|$))|(^2.6.[0-3](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB < 2.2.7 and < 2.4.9 which contain a data
    # integrity related bug involving mongos: SERVER-12146
    @classmethod
    def testMongoWritebackListener(cls, groupPing):
        if groupPing.group['shardCount'] == 0:
            return {'ok': True, 'payload': {'pass': True}}
        # <= 2.2.6, <= 2.4.8
        regex = '(^2.2.[0-6](-|$))|(^2.4.[0-8](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for a large number of MMS monitoring agents
    @classmethod
    def testNMonitoringAgents(cls, groupPing):
        if groupPing.group['activeAgentCount'] > 5:
            return {'ok': True, 'payload': {'pass': False}}
        return {'ok': True, 'payload': {'pass': True}}

    # tests if the index misses increased by indexMissIncreaseRatio in one day
    @classmethod
    def testIndexMissIncrease(cls, groupPing):
        
        # maximum allowed ratio increase between two datapoints
        indexMissIncreaseRatio = 10
        
        # dictionary of miss ratios by hid 
        missRatioDict = defaultdict(list)
        # dictionary of query times
        queryTimestampDict = defaultdict(list)
        # dictionary of ping IDs
        idsDict = defaultdict(list)

        def buildCurrentState(host):
            missRatio = host.getBtreeIndexMissRatio()
            pingTime = host.getPingTime()
            hid = host.getHostId()

            if not (pingTime and missRatio and hid):
                return None

            missRatioDict[hid].append(missRatio)
            queryTimestampDict[hid].append(pingTime)
            idsDict[hid].append(host.getId())

        while groupPing:
            groupPing.forEachHost(buildCurrentState)
            groupPing = groupPing.prev()

        res = True
        ids = []

        for hid in missRatioDict.keys():
            ratios = missRatioDict[hid]
            ts = queryTimestampDict[hid]
            pids = idsDict[hid]

            if len(ratios) < 2:
                # not enough datapoints for this node
                continue
            else:
                # at least 2 data points:
                for i in range(1, len(ratios)):
                    dt = (ts[i-1] - ts[i]).total_seconds()
                    dv = (ratios[i-1] - ratios[i])

                    if dv > indexMissIncreaseRatio * dt:
                        ids.append(pids[i-1])
                        ids.append(pids[i])
                        res = False

        return {'pass':  res, 'ids': list(set(ids))}

    @classmethod
    def testBackgroundFlushAverage(cls, groupPing):
        maxAcceptableBackgroundFlush = 30 * 1000  # in ms

        def checkBackgroundFlushAverage(host):
            serverStatus = host.getServerStatus()
            if serverStatus is None:
                return None
            if 'backgroundFlushing' not in serverStatus:
                return None

            if (serverStatus['backgroundFlushing']['average_ms']
                    > maxAcceptableBackgroundFlush):
                return False
            else:
                return True
        return groupPing.forEachHost(checkBackgroundFlushAverage)

    @classmethod
    def testRecentBackgroundFlushAverage(cls, groupPing):
        maxAcceptableBackgroundFlush = 30 * 1000  # in ms
        bFlushDocs = {}
        res = True
        ids = []

        def buildBackgroundFlushAverages(host):
            serverStatus = host.getServerStatus()
            if serverStatus is None:
                return None
            if 'backgroundFlushing' not in serverStatus:
                return None
            backgroundFlushing = serverStatus['backgroundFlushing']

            hid = host.getHostId()
            if hid not in bFlushDocs:
                bFlushDocs[hid] = {
                    'pingId': host.doc['_id'],
                    'count': 0,
                    'total': 0
                }
            bFlushDocs[hid]['count'] += 1
            bFlushDocs[hid]['total'] += float(backgroundFlushing['last_ms'])
            return True

        startDateTime = None
        while groupPing:
            groupPing.forEachHost(buildBackgroundFlushAverages)

            # Find a time for the current group ping if one exists
            index = 0
            keys = groupPing.pings.keys()
            currentPing = groupPing.pings[keys[index]]
            serverStatus = currentPing.getServerStatus()
            while index < len(groupPing.pings) and not serverStatus:
                index += 1
                currentPing = groupPing.pings[keys[index]]
                serverStatus = currentPing.getServerStatus()

            if serverStatus:
                # Store the current groupPing as the start
                # if we don't have a newest
                if not startDateTime:
                    startDateTime = serverStatus['localTime']

                # Stop traversing backward if the ping group is more
                # than an hour older than start
                if (currentPing.getServerStatus()['localTime']
                        < startDateTime - datetime.timedelta(hours=1)):
                    break
            groupPing = groupPing.prev()

        ok = len(bFlushDocs.values()) >= 2
        for bFlushDoc in bFlushDocs.values():
            if (bFlushDoc['total'] / bFlushDoc['count']
                    > maxAcceptableBackgroundFlush):
                res = False
                ids.append(bFlushDoc['pingId'])
        return {'ok': ok, 'payload': {'pass': res, 'ids': ids}}

    @classmethod
    def testVersionDifference(cls, groupPing):
        # Hash of version documents by hid
        vDocs = {}

        # Max acceptable difference in version array 2.6.8 = [2, 6, 8, 0]
        # Ex: 2.6.8 - 2.6.4 = [0, 0, 2, 0] which is less than [0, 0, 3, 3]
        maxAcceptableDifference = [0, 0, 3, 3]

        def buildCurrentState(host):
            serverStatus = host.getServerStatus()
            if serverStatus is None:
                return None

            buildInfo = host.getBuildInfo()
            if buildInfo is None:
                return None

            hid = host.getHostId()
            if hid not in vDocs:
                vDocs[hid] = {}
            # We're traversing backwards for each host looking for the
            # earliest occurrence of the current version on the node
            if 'version' not in vDocs[hid]:
                vDocs[hid]['version'] = buildInfo['versionArray']
            if vDocs[hid]['version'] == buildInfo['versionArray']:
                vDocs[hid]['since'] = serverStatus['localTime']
                vDocs[hid]['pingId'] = host.doc['_id']
            return True

        while groupPing:
            groupPing.forEachHost(buildCurrentState)
            groupPing = groupPing.prev()

        currentState = vDocs.values()
        currentState.sort(key=lambda vDoc: vDoc['version'], reverse=True)

        res = True
        ids = []

        for i, newVersionVDoc in enumerate(currentState):
            newVersion = newVersionVDoc['version']
            for olderVersionVDoc in currentState[i+1:len(currentState)]:
                olderVersion = olderVersionVDoc['version']
                versionDifference = [a - b for a, b in
                                     zip(newVersion, olderVersion)]
                timeDifference = (newVersionVDoc['since'] -
                                  olderVersionVDoc['since'])
                if (versionDifference > maxAcceptableDifference
                        and timeDifference > datetime.timedelta(days=1)):
                    res = False
                    ids.append(newVersionVDoc['pingId'])
                    ids.append(olderVersionVDoc['pingId'])

        return {'ok': True, 'payload': {'pass':  res, 'ids': list(set(ids))}}

    @classmethod
    def testLargeNonMappedMemory(cls, groupPing):
        def hasSmallNonMappedMemory(host):
            mappedMem = host.getMappedWithJournalMemory()
            # journaling not enabled
            if not mappedMem:
                mappedMem = host.getMappedMemory()
            virtualMem = host.getVirtualMemory()
            openConnections = host.getCurrentConnections()

            if mappedMem is not None and \
               virtualMem is not None and \
               openConnections is not None:
                # each open connection is allowed 1 MB
                # there may be a problem if non-mapped memory is more than 2GB
                return virtualMem - mappedMem - openConnections > 2048
            return True
        return groupPing.forEachHost(hasSmallNonMappedMemory)

    @classmethod

    def testNumMongos(cls, groupPing):
        ids = []
        for ping in groupPing.pings:
            if groupPing.pings[ping].isMongos():
                ids.append(ping)
                print ping
        return {'pass': len(ids) < 10, 'ids': ids}

    @classmethod
    def testSyncDelay(cls, groupPing):
        def hasDefaultSyncDelay(host):
            res = True
            doc = host.getGetParameterAll()
            if doc is not None and 'syncDelay' in doc:
                if doc['syncDelay'] != 60:
                    res = False
            return res
        return groupPing.forEachHost(hasDefaultSyncDelay)

    @classmethod
    def testNotableScan(cls, groupPing):
        def hasNoNotableScan(host):
            res = True
            doc = host.getGetParameterAll()
            if doc is not None and 'notableScan' in doc:
                res = not(doc['notableScan'])
            return res
        return groupPing.forEachHost(hasNoNotableScan)

    @classmethod
    def testDiagLogGreaterThanZero(cls, groupPing):
        def hasDiagLogGreaterThanZero(host):
            doc = host.getCmdLineOpts()
            if doc is not None and 'parsed' in doc:
                parsed = doc['parsed']
                if 'diaglog' in parsed and parsed['diaglog'] > 0:
                    return False
            return True
        return groupPing.forEachHost(hasDiagLogGreaterThanZero)

    @classmethod
    def testTimedoutCursors(cls, groupPing):
        def smallNumberofTimedoutCursors(host):

            numTimedout = host.getTimedoutCursorCount()
            # http://docs.mongodb.org/manual/core/cursors/
            # seems like cursors map to "query" operations, so this should
            # be a good estimate of the total number of cursors
            numTotal = host.getQueryOpCount()

            if numTimedout is None or numTotal is None:
                return None

            if float(numTimedout) / numTotal > 0.005:
                return False

            return True
        return groupPing.forEachHost(smallNumberofTimedoutCursors)

    # check for global lock percentage over 80% for over 10min
    # TODO: need to check that there's more than one DB,
    # https://jira.mongodb.org/browse/TSPROJ-98
    @classmethod
    def testHighGlobalLock(cls, groupPing):

        # dictionary of the query timestamp
        tsDict = defaultdict(list)
        # dictionary of global lock ratios
        lockRatioDict = defaultdict(list)
        # dictionary of ping IDs
        idsDict = defaultdict(list)

        def buildCurrentState(host):
            # not using the "ratio" subdocument since some pings don't have it
            # computing the ratio manually instead
            t1 = host.getGlobalLockLockTime()
            t2 = host.getGlobalLockTotalTime()
            pingTime = host.getPingTime()
            hid = host.getHostId()

            if None in [pingTime, hid]:
                return None

            if not t1 or not t2:
                return None

            ratio = float(t1)/t2

            tsDict[hid].append(pingTime)
            lockRatioDict[hid].append(ratio)
            idsDict[hid].append(host.getId())

        while groupPing:
            #TODO: only need to check the last 10 min worth of pings
            groupPing.forEachHost(buildCurrentState)
            groupPing = groupPing.prev()

        res = True
        ids = []

        pingRatioThreshold = 0.8

        for hid in lockRatioDict.keys():
            ratios = lockRatioDict[hid]
            ts = tsDict[hid]
            pids = idsDict[hid]

            # index of last timestamp of ping higher than the threshold
            highPingEndIndex = -1

            for i in range(len(ratios)):
                if ratios[i] > pingRatioThreshold:
                    highPingEndIndex = i
                elif highPingEndIndex != -1:
                    # if sustained for more than 10 min
                    if ts[highPingEndIndex] - ts[i] > 600:
                        for j in range(i, highPingEndIndex + 1):
                            ids.append(pids[j])
                            res = False
                    highPingEndIndex = -1

        return {'pass':  res, 'ids': ids}

    def testJournalCommitsInWriteLock(cls, groupPing):
        commitsInWriteLockByHost = {}

        def checkHostCommitsInWriteLock(host):
            serverStatus = host.getServerStatus()
            if serverStatus is None:
                return None

            pingId = host.doc['_id']
            hid = host.getHostId()
            if 'dur' not in serverStatus:
                return None
            dur = serverStatus['dur']

            commitsInWriteLock = dur['commitsInWriteLock']
            return commitsInWriteLock == 0

        return groupPing.forEachHost(checkHostCommitsInWriteLock)

    @classmethod
    def testChangeInJournalCommitsInWriteLock(cls, groupPing):
        commitsInWriteLockByHost = {}

        def buildCommitsByHost(host):
            serverStatus = host.getServerStatus()
            if serverStatus is None:
                return None

            pingId = host.doc['_id']
            hid = host.getHostId()
            if 'dur' not in serverStatus:
                return None
            dur = serverStatus['dur']

            localTime = serverStatus['localTime']
            commitsInWriteLock = dur['commitsInWriteLock']
            if hid not in commitsInWriteLockByHost:
                commitsInWriteLockByHost[hid] = []
            commitsInWriteLockByHost[hid].insert(0, {
                'time': localTime,
                'commits': commitsInWriteLock,
                'pingId': pingId
                })
            return True

        while groupPing:
            groupPing.forEachHost(buildCommitsByHost)
            groupPing = groupPing.prev()

        ok = True
        res = True
        ids = []
        for commitDocs in commitsInWriteLockByHost.values():
            if len(commitDocs) >= 2:
                for i in range(0, len(commitDocs) - 1):
                    dCommits = (commitDocs[i+1]['commits']
                                - commitDocs[i]['commits'])
                    dTime = commitDocs[i+1]['time'] - commitDocs[i]['time']
                    dTimeInHours = dTime.total_seconds() / 60 / 60
                    if dTimeInHours == 0:
                        continue
                    dCommitsPerHour = float(dCommits) / dTimeInHours
                    if abs(dCommitsPerHour) > 0:
                        res = False
                        ids.append(commitDocs[i+1]['pingId'])
                        ids.append(commitDocs[i]['pingId'])

        return {'ok': ok, 'payload': {'pass': res, 'ids': ids}}

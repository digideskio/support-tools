import re


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

    # This is a test for an even number of voting members in a replica set
    def testEvenVotingNumberReplicaSets(groupPing):
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

    # This is a test for ulimit-related warnings on startup
    def testLimitsStartupWarning(groupPing):
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
    def testMongo20ReplSetStepDown(groupPing):
        # <= 2.0.1
        regex = '^2.0.[01](-|$)'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.2.0 which contains idempotency and
    # replication bugs:
    # https://wiki.mongodb.com/display/cs/Idempotency+and+MongoDB+2.2+replication
    def testMongo22Idempotency(groupPing):
        # 2.2.0
        regex = '^2.2.0'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.x (x<5) which contains a security related
    # vulnerability wherein authentication takes a database lock it shouldn't:
    # SERVER-9983
    def testMongo24AuthDbLock(groupPing):
        # <= 2.4.4
        regex = '^2.4.[0-4](-|$)'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.x (x<8) which contains a dbhash cache bug
    # https://wiki.mongodb.com/display/cs/2.4.7+-+SERVER-11421+-+Cached+dbhash+for+the+config.chunks+collection+not+updated
    def testMongo24DbhashCache(groupPing):
        # <= 2.4.7
        regex = '^2.4.[0-7](-|$)'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.x (x<5) which contains a security related
    # vulnerability that could allow a remotely triggered seg fault in the JS
    # engine: SERVER-9878
    def testMongo24JSRemoteSegfault(groupPing):
        # <= 2.4.4
        regex = '^2.4.[0-4](-|$)'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.0 which contains an initial sync bug
    # SERVER-9087
    def testMongo24InitialSync(groupPing):
        # 2.4.0
        regex = '^2.4.0'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.0 which contains a data integreity related
    # bug re secondary indexes: SERVER-9087
    def testMongo24SecondaryIndexes(groupPing):
        # 2.4.0
        regex = '^2.4.0'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.6.0 which contains a security related
    # vulnerability re user credentials: SERVER-13644
    def testMongo26Credentials(groupPing):
        # 2.6.0
        regex = '^2.6.0'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.6.0 and 2.6.1 which contain an x.509
    # security related vulnerability: SERVER-13753
    def testMongo26X509Auth(groupPing):
        # <= 2.6.1
        regex = '^2.6.[01](-|$)'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB <= 2.2.3, 2.4.1 which contain a security
    # related vulnerability re JS function conflics in the mongo shell:
    # SERVER-9131
    # NOTE SERVER-9131 is in Planning Bucket A, is it even fair to limit to
    # these releases?
    def testMongoJSShellConflicts(groupPing):
        # <= 2.2.3, <= 2.4.1
        regex = '(^2.2.[0-3](-|$))|(^2.4.[01](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB < 2.2.6 and < 2.4.6 which contain a data
    # integrity related bug re large chunk migratoins: SERVER-10478
    def testMongoLargeChunkMigrations(groupPing):
        if groupPing.group['shardCount'] == 0:
            return {'pass': True}
        # <= 2.2.5, <= 2.4.5
        regex = '(^2.2.[0-5](-|$))|(^2.4.[0-5](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB <= 1.8.4 and <= 2.0.1 which contain a data
    # integrity related bug re missing documents on secondaries: SERVER-3956,
    # SERVER-4270
    # NOTE These SERVER tickets have different fix versions so we'll take the
    # later one to be more conservative
    def testMongoSecondaryMissingDocs(groupPing):
        # <= 1.8.4, <= 2.0.1
        regex = '(^1.8.[0-4](-|$))|(^2.0.[01](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB <= 2.0.8, 2.2.3, 2.4.1 which contain a
    # security related vulnerability re SpiderMonkey's JS nativeHelper
    # function: SERVER-9124
    def testMongoSMNativeHelper(groupPing):
        # <= 2.0.8, <= 2.2.3, <= 2.4.1
        regex = '(^2.0.[0-8](-|$))|(^2.2.[0-3](-|$))|(^2.4.[01](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB 2.4.[0-10] and 2.6.[0-3] which contain a data
    # integrity related bug re text-indexed fields: SERVER-14738
    def testMongoTextIndexedFields(groupPing):
        # <= 2.4.10, <= 2.6.3
        regex = '(^2.4.([0-9]|10)(-|$))|(^2.6.[0-3](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for MongoDB < 2.2.7 and < 2.4.9 which contain a data
    # integrity related bug involving mongos: SERVER-12146
    def testMongoWritebackListener(groupPing):
        if groupPing.group['shardCount'] == 0:
            return {'pass': True}
        # <= 2.2.6, <= 2.4.8
        regex = '(^2.2.[0-6](-|$))|(^2.4.[0-8](-|$))'
        return groupPing.forEachHost(GroupPingTests.isNotVersion, regex)

    # This is a test for a large number of MMS monitoring agents
    def testNMonitoringAgents(groupPing):
        if groupPing.group['activeAgentCount'] > 5:
            return {'pass': False}
        return {'pass': True}

    # This is a test for NUMA-related warnings on startup
    def testNumaStartupWarning(groupPing):
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
    def testStartupWarning(groupPing):
        def hasNoStartupWarning(host):
            doc = host.getStartupWarnings()
            if doc is not None and 'log' in doc:
                if len(doc['log']) != 0:
                    return False
            return True
        return groupPing.forEachHost(hasNoStartupWarning)

    def testNumReplicaSetWithMoreThanOneArbiter(groupPing):
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

    def testNumHostWithVotesMoreThanOne(groupPing):
        def hasLTE1Vote(host):
            res = True
            doc = host.getLocalSystemReplSet()
            if doc is not None and 'members' in doc:
                for member in doc['members']:
                    if 'votes' in member and member['votes'] > 1:
                        res = False
            return res
        return groupPing.forEachPrimary(hasLTE1Vote)

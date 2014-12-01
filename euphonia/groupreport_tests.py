import re


class GroupReportTests:
    # This is an organizational structure that strictly contains static methods
    # Note the convention: If it passes the test, then it returns True.
    # Otherwise, it returns false

    # This is a test for an even number of voting members in a replica set
    def testEvenVotingNumberReplicaSets(group):
        if group['NumEvenVotingNumberReplicaSets'] and\
                group['NumEvenVotingNumberReplicaSets'] != 0:
            return False
        return True

    # This is a test for ulimit-related warnings on startup
    def testLimitsStartupWarning(group):
        if group['NumActiveHostWithRlimitsStartupWarning'] and\
                group['NumActiveHostWithRlimitsStartupWarning'] != 0:
            return False
        return True

    # This is a test for MongoDB < 2.0.2 which contains a data integrity related
    # bug re open sockets on replSetStepDown: SERVER-4405
    def testMongo20ReplSetStepDown(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.0.1
                if re.match('^2.0.[01](-|$)', ver):
                    return False
        return True

    # This is a test for MongoDB 2.2.0 which contains idempotency and
    # replication bugs:
    # https://wiki.mongodb.com/display/cs/Idempotency+and+MongoDB+2.2+replication
    def testMongo22Idempotency(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # 2.2.0
                if re.match('^2.2.0', ver):
                    return False
        return True

    # This is a test for MongoDB 2.4.x (x<5) which contains a security related vulnerability
    # wherein authentication takes a database lock it shouldn't: SERVER-9983
    def testMongo24AuthDbLock(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.4.4
                if re.match('^2.4.[0-4](-|$)', ver):
                    return False
        return True

    # This is a test for MongoDB 2.4.x (x<8) which contains a dbhash cache bug
    # https://wiki.mongodb.com/display/cs/2.4.7+-+SERVER-11421+-+Cached+dbhash+for+the+config.chunks+collection+not+updated
    def testMongo24DbhashCache(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.4.7
                if re.match('^2.4.[0-7](-|$)', ver):
                    return False
        return True

    # This is a test for MongoDB 2.4.x (x<5) which contains a security related vulnerability
    # that could allow a remotely triggered seg fault in the JS engine: SERVER-9878
    def testMongo24JSRemoteSegfault(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.4.4
                if re.match('^2.4.[0-4](-|$)', ver):
                    return False
        return True

    # This is a test for MongoDB 2.4.0 which contains an initial sync bug
    # SERVER-9087
    def testMongo24InitialSync(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # 2.4.0
                if re.match('^2.4.0', ver):
                    return False
        return True

    # This is a test for MongoDB 2.4.0 which contains a data integreity related bug
    # re secondary indexes: SERVER-9087
    def testMongo24SecondaryIndexes(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # 2.4.0
                if re.match('^2.4.0', ver):
                    return False
        return True

    # This is a test for MongoDB 2.6.0 which contains a security related vulnerability
    # re user credentials: SERVER-13644
    def testMongo26Credentials(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # 2.6.0
                if re.match('^2.6.0', ver):
                    return False
        return True

    # This is a test for MongoDB 2.6.0 and 2.6.1 which contain an x.509 security related
    # vulnerability: SERVER-13753
    def testMongo26X509Auth(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.6.1
                if re.match('^2.6.[01](-|$)', ver):
                    return False
        return True

    # This is a test for MongoDB <= 2.2.3, 2.4.1 which contain a security related
    # vulnerability re JS function conflics in the mongo shell: SERVER-9131
    # NOTE SERVER-9131 is in Planning Bucket A, is it even fair to limit to these
    # releases?
    def testMongoJSShellConflicts(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.2.3
                if re.match('^2.2.[0-3](-|$)', ver):
                    return False
                # <= 2.4.1
                if re.match('^2.4.[01](-|$)', ver):
                    return False
        return True

    # This is a test for MongoDB < 2.2.6 and < 2.4.6 which contain a data integrity related
    # bug re large chunk migratoins: SERVER-10478
    def testMongoLargeChunkMigrations(group):
        if group['NumActiveShardedClusters'] > 0 and group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.2.5
                if re.match('^2.2.[0-5](-|$)', ver):
                    return False
                # <= 2.4.5
                if re.match('^2.4.[0-5](-|$)', ver):
                    return False
        return True

    # This is a test for MongoDB <= 1.8.4 and <= 2.0.1 which contain a data integrity related
    # bug re missing documents on secondaries: SERVER-3956, SERVER-4270
    # NOTE These SERVER tickets have different fix versions so we'll take the later one to be
    # more conservative
    def testMongoSecondaryMissingDocs(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 1.8.4
                if re.match('^1.8.[0-4](-|$)', ver):
                    return False
                # <= 2.0.1
                if re.match('^2.0.[01](-|$)', ver):
                    return False
        return True

    # This is a test for MongoDB <= 2.0.8, 2.2.3, 2.4.1 which contain a security related
    # vulnerability re SpiderMonkey's JS nativeHelper function: SERVER-9124
    def testMongoSMNativeHelper(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.0.8
                if re.match('^2.0.[0-8](-|$)', ver):
                    return False
                # <= 2.2.3
                if re.match('^2.2.[0-3](-|$)', ver):
                    return False
                # <= 2.4.1
                if re.match('^2.4.[01](-|$)', ver):
                    return False
        return True

    # This is a test for MongoDB 2.4.[0-10] and 2.6.[0-3] which contain a data integrity related
    # bug re text-indexed fields: SERVER-14738
    def testMongoTextIndexedFields(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.4.10
                if re.match('^2.4.([0-9]|10)(-|$)', ver):
                    return False
                # <= 2.6.3
                if re.match('^2.6.[0-3](-|$)', ver):
                    return False
        return True

    # This is a test for MongoDB < 2.2.7 and < 2.4.9 which contain a data integrity related
    # bug involving mongos: SERVER-12146
    def testMongoWritebackListener(group):
        if group['NumActiveShardedClusters'] > 0 and group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.2.6
                if re.match('^2.2.[0-6](-|$)', ver):
                    return False
                # <= 2.4.8
                if re.match('^2.4.[0-8](-|$)', ver):
                    return False
        return True

    # This is a test for a large number of MMS monitoring agents
    def testNMonitoringAgents(group):
        if group['NumActiveAgent'] and\
                group['NumActiveAgent'] > 5:
            return False
        return True

    # This is a test for NUMA-related warnings on startup
    def testNumaStartupWarning(group):
        if group['NumActiveHostWithNumaStartupWarning'] and\
                group['NumActiveHostWithNumaStartupWarning'] != 0:
            return False
        return True

    # This is a test for warnings on startup. It is inclusive to the NUMA and
    # Limits tests
    def testStartupWarning(group):
        if group['NumActiveHostWithStartupWarning'] and\
                group['NumActiveHostWithStartupWarning'] != 0:
            return False
        return True

    def testNumReplicaSetWithMoreThanOneArbiter(group):
        if group['NumReplicaSetWithMoreThanOneArbiter'] and\
                group['NumReplicaSetWithMoreThanOneArbiter'] != 0:
            return False
        return True

    def testNumHostWithVotesMoreThanOne(group):
        if group['NumHostWithMoreThanOneVote'] and\
                group['NumHostWithMoreThanOneVote'] != 0:
            return False
        return True

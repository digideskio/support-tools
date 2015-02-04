import re


class GroupReportTests:
    # MmsGroupReport := groupReport for short
    # Note the convention: If it passes the test, then it returns True.
    # Otherwise, it returns false

    # This is a test for an even number of voting members in a replica set
    @classmethod
    def testEvenVotingNumberReplicaSets(cls, groupReport):
        if groupReport.doc['NumEvenVotingNumberReplicaSets'] and\
                groupReport.doc['NumEvenVotingNumberReplicaSets'] != 0:
            return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for ulimit-related warnings on startup
    @classmethod
    def testLimitsStartupWarning(cls, groupReport):
        if groupReport.doc['NumActiveHostWithRlimitsStartupWarning'] and\
                groupReport.doc['NumActiveHostWithRlimitsStartupWarning'] != 0:
            return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB < 2.0.2 which contains a data integrity
    # related bug re open sockets on replSetStepDown: SERVER-4405
    @classmethod
    def testMongo20ReplSetStepDown(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.0.1
                if re.match('^2.0.[01](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB 2.2.0 which contains idempotency and
    # replication bugs:
    # https://wiki.mongodb.com/display/cs/Idempotency+and+MongoDB+2.2+replication
    @classmethod
    def testMongo22Idempotency(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # 2.2.0
                if re.match('^2.2.0', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB 2.4.x (x<5) which contains a security related
    # vulnerability wherein authentication takes a database lock it shouldn't:
    # SERVER-9983
    @classmethod
    def testMongo24AuthDbLock(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.4.4
                if re.match('^2.4.[0-4](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB 2.4.x (x<8) which contains a dbhash cache bug
    # https://wiki.mongodb.com/display/cs/2.4.7+-+SERVER-11421+-+Cached+dbhash+for+the+config.chunks+collection+not+updated
    @classmethod
    def testMongo24DbhashCache(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.4.7
                if re.match('^2.4.[0-7](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB 2.4.x (x<5) which contains a security related
    # vulnerability that could allow a remotely triggered seg fault in the JS
    # engine: SERVER-9878
    @classmethod
    def testMongo24JSRemoteSegfault(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.4.4
                if re.match('^2.4.[0-4](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB 2.4.0 which contains an initial sync bug
    # SERVER-9087
    @classmethod
    def testMongo24InitialSync(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # 2.4.0
                if re.match('^2.4.0', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB 2.4.0 which contains a data integreity related
    # bug re secondary indexes: SERVER-9087
    @classmethod
    def testMongo24SecondaryIndexes(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # 2.4.0
                if re.match('^2.4.0', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB 2.6.0 which contains a security related
    # vulnerability re user credentials: SERVER-13644
    @classmethod
    def testMongo26Credentials(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # 2.6.0
                if re.match('^2.6.0', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB 2.6.0 and 2.6.1 which contain an x.509
    # security related vulnerability: SERVER-13753
    @classmethod
    def testMongo26X509Auth(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.6.1
                if re.match('^2.6.[01](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB <= 2.2.3, 2.4.1 which contain a security
    # related vulnerability re JS function conflics in the mongo shell:
    # SERVER-9131
    # NOTE SERVER-9131 is in Planning Bucket A, is it even fair to limit to
    # these releases?
    @classmethod
    def testMongoJSShellConflicts(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.2.3
                if re.match('^2.2.[0-3](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
                # <= 2.4.1
                if re.match('^2.4.[01](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB < 2.2.6 and < 2.4.6 which contain a data
    # integrity related bug re large chunk migratoins: SERVER-10478
    @classmethod
    def testMongoLargeChunkMigrations(cls, groupReport):
        if groupReport.doc['NumActiveShardedClusters'] > 0 and\
                groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.2.5
                if re.match('^2.2.[0-5](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
                # <= 2.4.5
                if re.match('^2.4.[0-5](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB <= 1.8.4 and <= 2.0.1 which contain a data
    # integrity related bug re missing documents on secondaries: SERVER-3956,
    # SERVER-4270
    # NOTE These SERVER tickets have different fix versions so we'll take the
    # later one to be more conservative
    @classmethod
    def testMongoSecondaryMissingDocs(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 1.8.4
                if re.match('^1.8.[0-4](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
                # <= 2.0.1
                if re.match('^2.0.[01](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB <= 2.0.8, 2.2.3, 2.4.1 which contain a
    # security related vulnerability re SpiderMonkey's JS nativeHelper
    # function: SERVER-9124
    @classmethod
    def testMongoSMNativeHelper(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.0.8
                if re.match('^2.0.[0-8](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
                # <= 2.2.3
                if re.match('^2.2.[0-3](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
                # <= 2.4.1
                if re.match('^2.4.[01](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB 2.4.[0-10] and 2.6.[0-3] which contain a data
    # integrity related bug re text-indexed fields: SERVER-14738
    @classmethod
    def testMongoTextIndexedFields(cls, groupReport):
        if groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.4.10
                if re.match('^2.4.([0-9]|10)(-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
                # <= 2.6.3
                if re.match('^2.6.[0-3](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for MongoDB < 2.2.7 and < 2.4.9 which contain a data
    # integrity related bug involving mongos: SERVER-12146
    @classmethod
    def testMongoWritebackListener(cls, groupReport):
        if groupReport.doc['NumActiveShardedClusters'] > 0 and\
                groupReport.doc['MongoVersion']:
            vers = groupReport.doc['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.2.6
                if re.match('^2.2.[0-6](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
                # <= 2.4.8
                if re.match('^2.4.[0-8](-|$)', ver):
                    return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for a large number of MMS monitoring agents
    @classmethod
    def testNMonitoringAgents(cls, groupReport):
        if groupReport.doc['NumActiveAgent'] and\
                groupReport.doc['NumActiveAgent'] > 5:
            return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for NUMA-related warnings on startup
    @classmethod
    def testNumaStartupWarning(cls, groupReport):
        if groupReport.doc['NumActiveHostWithNumaStartupWarning'] and\
                groupReport.doc['NumActiveHostWithNumaStartupWarning'] != 0:
            return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    # This is a test for warnings on startup. It is inclusive to the NUMA and
    # Limits tests
    @classmethod
    def testStartupWarning(cls, groupReport):
        if groupReport.doc['NumActiveHostWithStartupWarning'] and\
                groupReport.doc['NumActiveHostWithStartupWarning'] != 0:
            return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    @classmethod
    def testNumReplicaSetWithMoreThanOneArbiter(cls, groupReport):
        if groupReport.doc['NumReplicaSetWithMoreThanOneArbiter'] and\
                groupReport.doc['NumReplicaSetWithMoreThanOneArbiter'] != 0:
            return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

    @classmethod
    def testNumHostWithVotesMoreThanOne(cls, groupReport):
        if groupReport.doc['NumHostWithMoreThanOneVote'] and\
                groupReport.doc['NumHostWithMoreThanOneVote'] != 0:
            return {'pass': False, 'ids': [groupReport.doc['_id']]}
        return {'pass': True}

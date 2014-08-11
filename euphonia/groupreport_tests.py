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

    # This is a test for MongoDB 2.4.x (x<8) which contains a dbhash cache bug
    # https://wiki.mongodb.com/display/cs/2.4.7+-+SERVER-11421+-+Cached+dbhash+for+the+config.chunks+collection+not+updated
    def testMongo24DbhashCache(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # <= 2.4.7
                if re.match('^2.4.[0-7]', ver):
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

    # This is a test for all not-most-recent 2.6.x instances
    def testMongo26(group):
        if group['MongoVersion']:
            vers = group['MongoVersion'].split('|')
            for ver in vers:
                # 2.6.x w/ x < 3
                if re.match('^2.6.([012]|3-)', ver):
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

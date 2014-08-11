from groupreport_tests import GroupReportTests


class GroupReport:
    def __init__(self, group):
        """ Build a GroupReport from a row in proactive.mmsgroupreports """
        # TODO validate named fields to guarantee schema across reports
        self.group = group
        # Currently supported tests, not all tests in GroupReportTests
        self.tests = ['EvenVotingNumberReplicaSets', 'LimitsStartupWarning',
                      'Mongo22Idempotency', 'Mongo24DbhashCache',
                      'Mongo24InitialSync', 'Mongo26', 'NMonitoringAgents',
                      'NumaStartupWarning', 'StartupWarning']
        self.verbose = False

    def runAllTests(self):
        res = {}
        for test in self.tests:
            res[test] = self.runTest(test)
        return res

    def runTest(self, test):
        if test in self.tests:
            fname = "test" + test
            if fname in dir(GroupReportTests):
                f = GroupReportTests.__dict__[fname]
                if self.verbose:
                    print "Testing " + test + "..."
                r = f(self.group)
                if self.verbose:
                    if r:
                        print "Passed!"
                    else:
                        print "Failed!"
                return r
            else:
                raise Exception(fname + " not defined")
        else:
            raise Exception(test + " not defined")

    # This is our schema. There are many like it but this one we're stuck with
    # :(
    fields = ['GroupId', 'GroupName', 'LastActiveAgentTime',
              'NumActiveMongos', 'NumTotalHosts', 'NumActiveAgent',
              'NumInactiveHost', 'NumActiveHost',
              'NumActiveStandaloneHost', 'NumActiveReplicaSets',
              'NumEvenNumberReplicaSets', 'NumActiveShardedClusters',
              'NumActiveHostWithStartupWarning', 'NumOpenAlerts',
              'BackupPricingEstimate', 'IsBackupCustomer', 'Campaigns',
              'IsPaid', 'LastPageView', 'NumHostWithStartupWarning',
              'numaStartupWarnings', 'rlimitsStartupWarnings',
              'startedWoReplSetStartupWarnings', 'MongoVersion',
              'NumHostWithVotesMoreThanOne',
              'NumReplicaSetWithMoreThanOneArbiter',
              'NumEvenVotingNumberReplicaSets',
              'NumDelayedMemberNotHidden', 'MaxReplicaSetVersion',
              'diaglog>0', 'syncdelay=0', 'notablescan', 'wo_configsvr',
              'noAutoSplit', 'UserId', 'UserEmail', 'FirstName',
              'LastName', 'IsCsCustomer', 'NumHostWithMoreThanOneVote',
              'IsBackupSetupStarted', 'NumEvenNumberReplicaSet',
              'NumActiveHostWithRlimitsStartupWarning',
              'NumActiveHostWithNumaStartupWarning']

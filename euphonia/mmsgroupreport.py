import grouptestdocument
import pymongo


class MmsGroupReport(grouptestdocument.GroupTestDocument):
    def __init__(self, groupId, tag=None, *args, **kwargs):
        self.tag = tag
        from mmsgroupreport_tests import MmsGroupReportTests
        grouptestdocument.GroupTestDocument.__init__(
            self, groupId=groupId,
            mongo=kwargs['mongo'],
            src='mmsgroupreports',
            testsLibrary=MmsGroupReportTests)

        match = {'GroupId': groupId}
        # If tag not specified get the latest entry by _id
        if tag is not None:
            match['tag'] = tag

        try:
            self.doc = next(self.mongo.euphonia.mmsgroupreports.find(match).
                            sort('_id', -1).limit(1), None)
        except pymongo.errors.PyMongoError as e:
            raise e

    def isCsCustomer(self):
        return self.doc['IsCsCustomer']

    def next(self):
        # TODO
        pass

    def prev(self):
        # TODO
        pass

    # This is our schema. There are many like it but this one we're stuck with
    # :(
    # TODO update or do away with this
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
              'NumActiveHostWithNumaStartupWarning',
              'MonitoringAgentVersion',
              'BackupAgentVersion']

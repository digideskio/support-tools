import dateutil

from datetime import datetime


def isMongoDBEmail(email):
    if email is not None and (email.endswith('@mongodb.com') or
                              email.endswith('@10gen.com')):
        return True
    return False


def isSlaQualifiedPartnerEmail(email):
    if email is not None and\
            email.lower() == 'nri-ossc-mongo-metlife-ext@nri.co.jp':
        return True
    return False


class SupportIssue:
    """ This is a Support issue. There are many like it but this one is mine.
    Use this to render the raw data needed to create tickets for specific
    ticketing systems, e.g. JIRA, and also as a wrapper for all ticket types
    """
    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return self.id.__hash__()

    def __init__(self, fields={}):
        self.doc = None
        self.fields = fields

    def fromDoc(self, doc):
        """ This method expects a document from MongoDB, i.e.
        support.issues.findOne() """
        self.doc = doc

        if self.hasJIRA():
            # normalize date fields
            created = self.doc['jira']['fields']['created']
            if not isinstance(created, datetime):
                created = dateutil.parser.parse(created).astimezone(
                    dateutil.tz.tzutc()).replace(tzinfo=None)
                self.doc['jira']['fields']['created']

            updated = self.doc['jira']['fields']['updated']
            if not isinstance(updated, datetime):
                updated = dateutil.parser.parse(updated).astimezone(
                    dateutil.tz.tzutc()).replace(tzinfo=None)
                self.doc['jira']['fields']['updated']

            return self

        return None

    def hasJIRA(self):
        """ Returns true if JIRA-specific informaton is present """
        return self.doc is not None and 'jira' in self.doc

    def hasKarakuri(self):
        """ Returns true if Karakuri-specific informaton is present """
        return self.doc is not None and 'karakuri' in self.doc

    def hasSLA(self):
        """ Returns true if SLA-specific informaton is present """
        return self.doc is not None and 'sla' in self.doc

    # TODO is this too dashboard specific to keep here?
    def isFTS(self):
        return 'fs' in self.labels

    def isProactive(self):
        if self.issuetype.lower() == 'proactive' and\
                isMongoDBEmail(self.reporterEmail):
            return True
        return False

    #
    # Begin properties
    #

    @property
    # TODO remove this when dashboard is updated to use assigneeName
    def assignee(self):
        return self.assigneeName

    @property
    def assigneeName(self):
        if self.hasJIRA():
            if 'assignee' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['assignee']:
                return self.doc['jira']['fields']['assignee']['name']
        return None

    @property
    def assigneeEmail(self):
        if self.hasJIRA():
            if 'assignee' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['assignee']:
                return self.doc['jira']['fields']['assignee'][
                    'emailAddress']
        return None

    @property
    def company(self):
        if self.hasJIRA():
            if 'customfield_10030' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['customfield_10030']:
                return self.doc['jira']['fields']['customfield_10030'][
                    'name']
        return None

    @property
    def created(self):
        if self.hasJIRA():
            if 'created' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['created']:
                return self.doc['jira']['fields']['created']
        return None

    @property
    def components(self):
        if self.hasJIRA():
            if 'components' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['components']:
                # TODO can we return the array instead of build a new one?
                return map(lambda x: x['name'], self.doc['jira']['fields'][
                    'components'])
            return []
        return None

    @property
    def earliestOfLastCustomerComments(self):
        if self.hasJIRA():
            comments = self.doc['jira']['fields']['comment']['comments']

            # Build up a stack of comments without dev-only to make this easier
            customer_relevant_comments = []
            for j in range(len(comments)):
                comment = comments[j]
                comment['cidx'] = j
                if 'visibility' not in comment or\
                        comment['visibility']['value'] != 'Developers':
                    customer_relevant_comments.append(comment)

            for i in range(len(customer_relevant_comments) - 1, -1, -1):
                currCommentAuthEmail = customer_relevant_comments[i]['author'][
                    'emailAddress']

                if not isMongoDBEmail(currCommentAuthEmail):
                    if i >= 1:
                        prevCommentAuthEmail = customer_relevant_comments[i-1][
                            'author']['emailAddress']

                        if not isMongoDBEmail(prevCommentAuthEmail):
                            continue

                    return {'created': customer_relevant_comments[i]
                            ['created'], 'cidx':
                            customer_relevant_comments[i]['cidx']}
        return None

    @property
    def firstCustomerComment(self):
        if self.hasJIRA():
            comments = self.doc['jira']['fields']['comment']['comments']

            for i in range(len(comments)):
                if 'visibility' not in comments[i] or\
                        comments[i]['visibility']['value'] != 'Developers':
                    email = comments[i]['author']['emailAddress']

                    if not isMongoDBEmail(email):
                        return {'created': comments[i]['created'], 'cidx': i}
        return None

    @property
    def firstXGenPublicComment(self):
        if self.hasJIRA():
            comments = self.doc['jira']['fields']['comment']['comments']

            for i in range(len(comments)):
                comment = comments[i]
                if 'visibility' not in comment or\
                        comment['visibility']['value'] != 'Developers':
                    email = comment['author']['emailAddress']

                    if isMongoDBEmail(email) or\
                            isSlaQualifiedPartnerEmail(email):
                        return {'created': comment['created'], 'cidx': i}
        return None

    @property
    def firstXGenPublicCommentAfterCustomerComment(self):
        """ Return the first MongoDB, Inc. public comment issued after the
        first customer comment """
        fcc = self.firstCustomerComment

        # If there is no customer comment then there can be no first xgen
        # public comment after customer comment
        if fcc:
            if self.hasJIRA():
                cidx = fcc['cidx']
                comments = self.doc['jira']['fields']['comment'][
                    'comments']

                for i in range(cidx+1, len(comments), 1):
                    comment = comments[i]
                    if 'visibility' not in comment or\
                            comment['visibility']['value'] != 'Developers':
                        email = comment['author']['emailAddress']

                        if isMongoDBEmail(email) or\
                                isSlaQualifiedPartnerEmail(email):
                            return {'created': comment['created'], 'cidx': i}
        return None

    @property
    # NOTE support dashboard might be using this for something
    # else and require moving to issueId (see below)
    def id(self):
        if self.doc:
            return self.doc['_id']
        return None

    @property
    def issueId(self):
        if self.hasJIRA():
            return self.doc['jira']['id']
        return None

    # TODO remove when dashboard is updated to use isFTS()
    @property
    def is_fts(self):
        return self.isFTS()

    @property
    def issuetype(self):
        if self.hasJIRA():
            if 'issuetype' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['issuetype']:
                # sub-tasks of proactive tickets are also proactive
                if self.doc['jira']['fields']['issuetype']['name'] ==\
                        'Sub-task' and self.parentIssuetype == 'Proactive':
                    return self.parentIssuetype
                return self.doc['jira']['fields']['issuetype']['name']
        return None

    @property
    # TODO I believe the dashboard is using this but it can moved to
    # key (see below) and this can be dropped
    def jiraKey(self):
        if self.hasJIRA():
            return self.doc['jira']['key']
        return None

    @property
    def key(self):
        if self.hasJIRA():
            return self.doc['jira']['key']
        return None

    @property
    def labels(self):
        if self.hasJIRA():
            if 'labels' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['labels']:
                # TODO is this clean? (see components too)
                out = []
                map(out.append, self.doc['jira']['fields']['labels'])
                return out
            return []
        return None

    @property
    def lastCustomerComment(self):
        if self.hasJIRA():
            comments = self.doc['jira']['fields']['comment']['comments']

            for i in range(len(comments) - 1, -1, -1):
                if 'visibility' not in comments[i] or\
                        comments[i]['visibility']['value'] != 'Developers':
                    email = comments[i]['author']['emailAddress']

                    if not isMongoDBEmail(email):
                        return {'updated': comments[i]['updated'], 'cidx': i}
        return None

    @property
    def lastXGenPublicComment(self):
        if self.hasJIRA():
            comments = self.doc['jira']['fields']['comment']['comments']

            for i in range(len(comments) - 1, -1, -1):
                if 'visibility' not in comments[i] or\
                        comments[i]['visibility']['value'] != 'Developers':
                    email = comments[i]['author']['emailAddress']

                    if isMongoDBEmail(email) or\
                            isSlaQualifiedPartnerEmail(email):
                        return {'created': comments[i]['created'], 'cidx': i}
        return None

    @property
    def lastXGenOnlyComment(self):
        if self.hasJIRA():
            comments = self.doc['jira']['fields']['comment']['comments']

            for i in range(len(comments) - 1, -1, -1):
                if 'visibility' in comments[i] and\
                        comments[i]['visibility']['value'] == 'Developers':
                    email = comments[i]['author']['emailAddress']

                    if isMongoDBEmail(email) or\
                            isSlaQualifiedPartnerEmail(email):
                        return {'author': {'displayName': comments[i][
                            'author']['displayName']}, 'cidx': i}
        return None

    @property
    def owner(self):
        if self.hasJIRA():
            if 'customfield_10041' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['customfield_10041']:
                return self.doc['jira']['fields']['customfield_10041'][
                    'name']
        return None

    @property
    def parentIssuetype(self):
        if self.hasJIRA():
            if 'parent' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['parent']:
                return self.doc['jira']['fields']['parent']['fields'][
                    'issuetype']['name']
        return None

    @property
    def priority(self):
        if self.hasJIRA():
            if 'priority' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['priority']:
                return int(self.doc['jira']['fields']['priority']['id'])
        return None

    @property
    def project(self):
        if self.hasJIRA():
            if 'project' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['project']:
                return self.doc['jira']['fields']['project']['key']
        return None

    @property
    def reporterEmail(self):
        if self.hasJIRA():
            if 'reporter' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['reporter']:
                return self.doc['jira']['fields']['reporter'][
                    'emailAddress']
        return None

    @property
    def reporterName(self):
        if self.hasJIRA():
            if 'reporter' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['reporter']:
                return self.doc['jira']['fields']['reporter']['name']
        return None

    # TODO improve this on the dashboard-side as
    # this looks funny and may not be efficient!
    @property
    def reporterSummaryDescription(self):
        if self.hasJIRA():
            if 'summary' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']:
                return {'value': self.doc['jira']['fields']['summary']}
        return None

    @property
    def sla(self):
        if self.hasSLA():
            return self.doc['sla']
        return None

    @property
    def status(self):
        if self.hasJIRA():
            if 'status' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['status']:
                return self.doc['jira']['fields']['status']['name']
        return None

    # TODO is this actually used by the dashboard?
    @property
    def tags(self):
        if self.hasJIRA():
            # TODO is this a real field? i can't find an example
            if 'tags' in self.doc['jira'] and\
                    self.doc['tags']:
                return self.doc['jira']['tags']
            return []
        return None

    @property
    def updated(self):
        if self.hasJIRA():
            if 'updated' in self.doc['jira']['fields'] and\
                    self.doc['jira']['fields']['updated']:
                return self.doc['jira']['fields']['updated']
        return None

    #
    # End properties
    #

    #
    # JIRA speficic
    #

    def getJIRAFields(self):
        """ Return a fields dict that can be passed directly to the
        JIRA.create_issue method as the fields argument """
        fields = {}

        # TODO return from existing jira doc
        if self.hasJIRA():
            pass

        for field in self.fields:
            setter = self.getJIRASetter(field)
            if setter:
                setter(fields, self.fields[field])
            else:
                # TODO continue without field?
                raise Exception("field %s not supported in getJIRAFields" %
                                field)

        return fields

    def getJIRASetter(self, field):
        """ Return the appropriate JIRA-specific setter for the given field """
        set_map = {'description': self.setJIRADescription,
                   'group': self.setJIRAGroup,
                   'issuetype': self.setJIRAIssuetype,
                   'labels': self.setJIRALabels,
                   'owner': self.setJIRAOwner,
                   'priority': self.setJIRAPriority,
                   'project': self.setJIRAProject,
                   'reporter': self.setJIRAReporter,
                   'summary': self.setJIRASummary,
                   'company groups': self.setJIRACompanyGroups
                   }

        if field in set_map:
            return set_map[field]
        else:
            return None

    def setJIRADescription(self, fields, description):
        fields['description'] = description

    def setJIRAGroup(self, fields, group):
        fields['customfield_10030'] = {'name': group}

    def setJIRAIssuetype(self, fields, issueType):
        fields['issuetype'] = {'name': issueType}

    def setJIRALabels(self, fields, labels):
        """ This is a placeholder for the parameter. Labels is set via update
        """
        # TODO is this really true?
        pass

    def setJIRAOwner(self, fields, owner):
        """ This is a placeholder for the parameter. Owner is set via Internal
        Fields transition """
        pass

    def setJIRAPriority(self, fields, priority):
        # TODO make sure this works!
        fields['priority'] = str(priority)

    def setJIRAProject(self, fields, project):
        fields['project'] = {'key': project}

    def setJIRAReporter(self, fields, reporter):
        fields['reporter'] = {'name': reporter}

    def setJIRASummary(self, fields, summary):
        fields['summary'] = summary

    def setJIRACompanyGroups(self, fields, companyGroups):
        fields['customfield_10850'] = {'name': companyGroups}

    #
    # Karakuri specific
    #

    def isActive(self):
        if not self.hasKarakuri() or 'sleep' not in self.doc['karakuri']:
            return True

        wakeDate = self.doc['karakuri']['sleep']

        if not isinstance(wakeDate, datetime):
            return False

        if wakeDate <= datetime.utcnow():
            # TODO wake up! i.e. drop sleep
            return True
        else:
            return False

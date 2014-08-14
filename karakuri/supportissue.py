import copy
import dateutil

from datetime import datetime


# TODO move these somewhere else
def isMongoDBEmail(email):
    if email is not None and (email.endswith('@mongodb.com') or
                              email.endswith('@10gen.com')):
        return True
    return False


def isSlaQualifiedPartnerEmail(email):
    if email.lower() == 'nri-ossc-mongo-metlife-ext@nri.co.jp':
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

    # TODO improve this
    def __init__(self, params={}):
        self.jiradoc = None
        self.params = params

    #
    # Begin properties
    #

    @property
    # TODO change this to assigneeName
    def assignee(self):
        if self.jiradoc:
            if 'assignee' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['assignee']:
                return self.jiradoc['jira']['fields']['assignee']['name']
        return None

    @property
    def assigneeEmail(self):
        if self.jiradoc:
            if 'assignee' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['assignee']:
                return self.jiradoc['jira']['fields']['assignee'][
                    'emailAddress']
        return None

    @property
    def company(self):
        if self.jiradoc:
            if 'customfield_10030' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['customfield_10030']:
                return self.jiradoc['jira']['fields']['customfield_10030'][
                    'name']
        return None

    @property
    def created(self):
        if self.jiradoc:
            if 'created' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['created']:
                return self.jiradoc['jira']['fields']['created']
        return None

    @property
    def components(self):
        if self.jiradoc:
            if 'components' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['components']:
                return map(lambda x: x['name'], self.jiradoc['jira']['fields'][
                    'components'])
            return []
        return None

    @property
    def earliestOfLastCustomerComments(self):
        if self.jiradoc:
            comments = self.jiradoc['jira']['fields']['comment']['comments']

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
                    prevCommentAuthEmail = customer_relevant_comments[i-1][
                        'author']['emailAddress']

                    if isMongoDBEmail(prevCommentAuthEmail) or i - 1 < 0:
                        return {'created': customer_relevant_comments[i]
                                ['created'], 'cidx':
                                customer_relevant_comments[i]['cidx']}
        return None

    @property
    def firstCustomerComment(self):
        if self.jiradoc:
            comments = self.jiradoc['jira']['fields']['comment']['comments']

            for i in range(0, len(comments), 1):
                if 'visibility' not in comments[i] or\
                        comments[i]['visibility']['value'] != 'Developers':
                    email = comments[i]['author']['emailAddress']

                    if not isMongoDBEmail(email):
                        return {'created': comments[i]['created'], 'cidx': i}
        return None

    @property
    def firstXGenPublicComment(self):
        if self.jiradoc:
            comments = self.jiradoc['jira']['fields']['comment']['comments']

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
            if self.jiradoc:
                cidx = fcc['cidx']
                comments = self.jiradoc['jira']['fields']['comment'][
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
    # else and require moving to ticketId()
    def id(self):
        # TODO generalize this to ticket_id
        if self.jiradoc:
            # id always exists
            # TODO raise exception if it doesn't
            return self.jiradoc['_id']
        return None

    @property
    def ticketId(self):
        # TODO generalize this to ticket_id
        if self.jiradoc:
            # id always exists
            # TODO raise exception if it doesn't
            return self.jiradoc['jira']['id']
        return None

    # TODO too dashboard specific for this class to be a property?
    # on the same level as isProactive methinks?
    @property
    def is_fts(self):
        return 'fs' in self.labels

    @property
    def issuetype(self):
        if self.jiradoc:
            if 'issuetype' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['issuetype']:
                # sub-tasks of proactive tickets are also proactive
                if self.jiradoc['jira']['fields']['issuetype']['name'] ==\
                        'Sub-task' and self.parentIssuetype == 'Proactive':
                    return self.parentIssuetype
                return self.jiradoc['jira']['fields']['issuetype']['name']
        return None

    @property
    def jiraKey(self):
        if self.jiradoc:
            # key always exists
            # TODO raise exception if it doesn't
            return self.jiradoc['jira']['key']
        return None

    @property
    def key(self):
        return self.jiraKey

    @property
    def labels(self):
        if self.jiradoc:
            if 'labels' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['labels']:
                # TODO is this necessary? would returning labels return
                # a reference instead of a copy? if that's true we need
                # to be more careful about this everywhere
                out = []
                map(out.append, self.jiradoc['jira']['fields']['labels'])
                return out
            return []
        return None

    @property
    def lastCustomerComment(self):
        if self.jiradoc:
            comments = self.jiradoc['jira']['fields']['comment']['comments']

            for i in range(len(comments) - 1, -1, -1):
                if 'visibility' not in comments[i] or\
                        comments[i]['visibility']['value'] != 'Developers':
                    email = comments[i]['author']['emailAddress']

                    if not isMongoDBEmail(email):
                        return {'updated': comments[i]['updated'], 'cidx': i}
        return None

    @property
    def lastXGenPublicComment(self):
        if self.jiradoc:
            comments = self.jiradoc['jira']['fields']['comment']['comments']

            for i in range(len(comments) - 1, -1, -1):
                if 'visibility' not in comments[i] or\
                        comments[i]['visibility']['value'] != 'Developers':
                    email = comments[i]['author'].get('emailAddress', None)

                    if isMongoDBEmail(email) or\
                            isSlaQualifiedPartnerEmail(email):
                        return {'created': comments[i]['created'], 'cidx': i}
        return None

    @property
    def lastXGenOnlyComment(self):
        if self.jiradoc:
            comments = self.jiradoc['jira']['fields']['comment']['comments']
            last_devonly_index = None

            # Record location of last dev-only comment and use to combine with
            # hypothesis
            hypothesis_index = None
            for i in range(len(comments) - 1, -1, -1):
                if 'visibility' in comments[i] and\
                        comments[i]['visibility']['value'] == 'Developers':
                    last_devonly_index = i
                    break

            if last_devonly_index is None:
                return None
            else:
                returned_object = copy.deepcopy(comments[last_devonly_index])

            # TODO do we still need all this hypothesis shit?
            if hypothesis_index is not None:
                # If the last dev only comment is also a hypothesis, just show
                # it
                if hypothesis_index == last_devonly_index:
                    returned_object = copy.deepcopy(comments[hypothesis_index])
                    returned_object['author']['displayName'] = (
                        returned_object.get('author').get('displayName')
                        + ' (+Hypothesis)')
                else:
                    if (returned_object.get('author').get('displayName') ==
                        comments[hypothesis_index].get('author').get(
                            'displayName')):
                        returned_object['author']['displayName'] = (
                            returned_object.get('author').get('displayName') +
                            ' (+separate Hypothesis)')
                        returned_object['body'] = (
                            returned_object.get('body') +
                            comments[hypothesis_index].get('body'))
                    else:
                        returned_object['author']['displayName'] = (
                            returned_object.get('author').get('displayName') +
                            ' (+separate Hypothesis)')
                        returned_object['body'] = (
                            comments[last_devonly_index].get(
                                'author').get('displayName') + 'said:' +
                            returned_object.get('body') +
                            comments[hypothesis_index].get('author').get('\
                                    displayName') + ' hypothesized:' +
                            comments[hypothesis_index].get('body'))
            return {'author': {'displayName': returned_object['author'][
                'displayName']}, 'cidx': last_devonly_index}
        return None

    @property
    def owner(self):
        if self.jiradoc:
            if 'customfield_10041' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['customfield_10041']:
                return self.jiradoc['jira']['fields']['customfield_10041'][
                    'name']
        return None

    @property
    def parentIssuetype(self):
        if self.jiradoc:
            if 'parent' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['parent']:
                return self.jiradoc['jira']['fields']['parent']['fields'][
                    'issuetype']['name']
        return None

    @property
    def priority(self):
        if self.jiradoc:
            if 'priority' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['priority']:
                return int(self.jiradoc['jira']['fields']['priority']['id'])
        return None

    @property
    def project(self):
        if self.jiradoc:
            if 'project' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['project']:
                return self.jiradoc['jira']['fields']['project']['key']
        return None

    @property
    def reporterEmail(self):
        if self.jiradoc:
            if 'reporter' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['reporter']:
                return self.jiradoc['jira']['fields']['reporter'][
                    'emailAddress']
        return None

    @property
    def reporterName(self):
        if self.jiradoc:
            if 'reporter' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['reporter']:
                return self.jiradoc['jira']['fields']['reporter']['name']
        return None

    # TODO improve this on the dashboard-side as
    # this looks funny and may not be efficient
    @property
    def reporterSummaryDescription(self):
        if self.jiradoc:
            if 'summary' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']:
                return {'value': self.jiradoc['jira']['fields']['summary']}
        return None

    @property
    def status(self):
        if self.jiradoc:
            if 'status' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['status']:
                return self.jiradoc['jira']['fields']['status']['name']
        return None

    # TODO is this actually used by the dashboard?
    @property
    def tags(self):
        if self.jiradoc:
            # TODO is this a real field? i can't find an example
            if 'tags' in self.jiradoc['jira'] and\
                    self.jiradoc['tags']:
                return self.jiradoc['jira']['tags']
            return []
        return None

    @property
    def updated(self):
        if self.jiradoc:
            if 'updated' in self.jiradoc['jira']['fields'] and\
                    self.jiradoc['jira']['fields']['updated']:
                return self.jiradoc['jira']['fields']['updated']
        return None

    #
    # End properties
    #

    def isProactive(self):
        if self.issuetype.lower() == 'proactive' and\
                isMongoDBEmail(self.reporterEmail):
            return True
        return False

    def fromJIRADoc(self, doc):
        """ This method expects a document from MongoDB, i.e.
        support.issues.find({}, {'jira':1}) """
        self.jiradoc = doc
        self._id = doc['_id']
        # TODO add protections to ensure proper jira doc!

        # normalize date fields
        created = self.jiradoc['jira']['fields']['created']
        if not isinstance(created, datetime):
            created = dateutil.parser.parse(created).astimezone(
                dateutil.tz.tzutc()).replace(tzinfo=None)
            self.jiradoc['jira']['fields']['created']

        updated = self.jiradoc['jira']['fields']['updated']
        if not isinstance(updated, datetime):
            updated = dateutil.parser.parse(updated).astimezone(
                dateutil.tz.tzutc()).replace(tzinfo=None)
            self.jiradoc['jira']['fields']['updated']

        return self

    def getJIRAFields(self):
        """ Return a fields dict that can be passed directly to the
        JIRA.create_issue method as the fields argument """
        fields = {}

        # TODO return from existing jira doc
        if self.jiradoc:
            pass

        for param in self.params:
            setter = self.getJIRASetter(param)
            if setter:
                setter(fields, self.params[param])
            else:
                # TODO continue without param?
                raise Exception("param %s not supported in getJIRAFields" %
                                param)

        return fields

    def getJIRASetter(self, param):
        """ Return the appropriate JIRA-specific setter for the given param """
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

        if param in set_map:
            return set_map[param]
        else:
            return None

    def setJIRADescription(self, data, description):
        data['description'] = description

    def setJIRAGroup(self, data, group):
        data['customfield_10030'] = {'name': group}

    def setJIRAIssuetype(self, data, issueType):
        data['issuetype'] = {'name': issueType}

    def setJIRALabels(self, data, labels):
        """ This is a placeholder for the parameter. Labels is set via update
        """
        # TODO is this really true?
        pass

    def setJIRAOwner(self, data, owner):
        """ This is a placeholder for the parameter. Owner is set via Internal
        Fields transition """
        pass

    def setJIRAPriority(self, data, priority):
        # TODO make sure this works!
        data['priority'] = str(priority)

    def setJIRAProject(self, data, project):
        data['project'] = {'key': project}

    def setJIRAReporter(self, data, reporter):
        data['reporter'] = {'name': reporter}

    def setJIRASummary(self, data, summary):
        data['summary'] = summary

    def setJIRACompanyGroups(self, data, companyGroups):
        data['customfield_10850'] = companyGroups

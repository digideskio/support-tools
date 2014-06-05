from pprint import pprint


class JIRAIssue:
    """ This is a JIRA ticket. There are many like it but this one is mine. """
    def __init__(self, jira, params={}):
        # jira is an instance of jira.client.JIRA
        self.jira = jira
        self.data = {}

        for param in params:
            if param == "group":
                key = "customfield_10030"
                value = {'name': params[param]}
            elif param == "owner":
                key = "customfield_10041"
                value = {'name': params[param]}
            else:
                key = param
                value = params[param]

            self.data[key] = value

    def dump(self):
        pprint(self.data)

    def setDescription(self, description):
        self.data['description'] = description

    def setGroup(self, group):
        if 'customfield_10030' in self.data:
            self.data['customfield_10030']['name'] = group
        else:
            self.data['customfield_10030'] = {'name': group}

    def setIssueType(self, issueType):
        if 'issuetype' in self.data:
            self.data['issuetype']['name'] = issueType
        else:
            self.data['issuetype'] = {'name': issueType}

    def setOwner(self, owner):
        if 'customfield_10041' in self.data:
            self.data['customfield_10041']['name'] = owner
        else:
            self.data['customfield_10041'] = {'name': owner}

    def setPriority(self, priority):
        self.data['priority'] = self.jira.priority(str(priority)).raw

    def setProject(self, project):
        if 'project' in self.data:
            self.data['project']['key'] = project
        else:
            self.data['project'] = {'key': project}

    def setReporter(self, reporter):
        if 'reporter' in self.data:
            self.data['reporter']['name'] = reporter
        else:
            self.data['reporter'] = {'name': reporter}

    def setSummary(self, summary):
        self.data['summary'] = summary

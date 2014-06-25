import sys

from pprint import pprint


class JIRAIssue:
    """ This is a JIRA ticket. There are many like it but this one is mine. """
    def getSetter(self, param):
        set_map = {'description': self.setDescription,
                   'group': self.setGroup,
                   'issuetype': self.setIssuetype,
                   'labels': self.setLabels,
                   'owner': self.setOwner,
                   'priority': self.setPriority,
                   'project': self.setProject,
                   'reporter': self.setReporter,
                   'summary': self.setSummary,
                   # DAN tickets
                   'company groups': self.setCompanyGroups
                   }
        if param.lower() in set_map:
            return set_map[param.lower()]
        else:
            None

    def __init__(self, jira, params={}):
        # jira is an instance of jira.client.JIRA
        self.jira = jira
        self.data = {}

        for param in params:
            if params[param] is not None:
                setter = self.getSetter(param)
                if setter:
                    setter(params[param])
                else:
                    print "Error: param %s not supported" % param
                    sys.exit(2)

    def dump(self):
        pprint(self.data)

    def setDescription(self, description):
        self.data['description'] = description

    def setGroup(self, group):
        if 'customfield_10030' in self.data:
            self.data['customfield_10030']['name'] = group
        else:
            self.data['customfield_10030'] = {'name': group}

    def setIssuetype(self, issueType):
        if 'issuetype' in self.data:
            self.data['issuetype']['name'] = issueType
        else:
            self.data['issuetype'] = {'name': issueType}

    def setLabels(self, labels):
        """ This is a placeholder for the parameter. Labels is set via update
        """
        pass

    def setOwner(self, owner):
        """ This is a placeholder for the parameter. Owner is set via Internal
        Fields transition """
        pass

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

    def setCompanyGroups(self, companyGroups):
        self.data['customfield_10850'] = companyGroups

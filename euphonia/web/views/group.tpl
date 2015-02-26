<%
import datetime

def getTimestamp(objectId):
    tmp = objectId.__str__()
    tmp = tmp[:8]
    return int(tmp, 16)
end

def getDatetime(objectId):
    n = getTimestamp(objectId)
    print(dir(datetime))
    return datetime.datetime.fromtimestamp(n)
end

def getNTests(type):
    n = 0

    src = None
    if type == 'failed' or type == 'ticketed':
        src = group['failedTests']
    elif type == 'resolved':
        src = group['resolvedTests']
        else:
        return n
    end

    for test in src:
        ticketed = test.get('ticket')
        if type == 'ticketed' and ticketed is None:
            continue
        end
        resolved = test.get('resolved')
        if type == 'resolved' and resolved is None:
            continue
        end
        if type == 'failed' and (ticketed is not None or resolved is not None):
            continue
        end
        n += 1
    end
    return n
end

def showTests(type):
    src = None
    if type == 'failed' or type == 'ticketed':
        src = group['failedTests']
    elif type == 'resolved':
        src = group['resolvedTests']
    end

    for test in src:
        ticketed = test.get('ticket')
        if type == 'ticketed' and ticketed is None:
            continue
        end
        resolved = test.get('resolved')
        if type == 'resolved' and resolved is None:
            continue
        end
        if type == 'failed' and (ticketed is not None or resolved is not None):
            continue
        end

        testName = test['test']
        testSrc = test['src']
        testComment = testDescriptionCache[testSrc][testName]['comment']
        testHeader = testDescriptionCache[testSrc][testName]['header']
        testId = test.get('ftid')
        if testId is None:
            testId = test.get('_id')
        end
        failedTs = getDatetime(testId)
        testIgnore = test.get('ignore', None)
        testNids = test['nids']

        # A ticket already exists for this test
        testClass = ""
        if ticketed is not None:
            ticketKey = ticketed.get('key')
            ticketTs = ticketed.get('ts').replace(microsecond=0)
            testClass = "alert-warning"
        end
        if resolved is not None:
            testClass = "alert-success"
        end
%>
<div id="div_failedTests_{{testId}}", class="alert {{testClass}}">
<%
        nfailedSpan = "%s" % testNids
%>
    <span id="div_failedTests_{{testId}}_title" class="h4">{{!testName}} <a data-toggle="collapse" href="#collapse{{testId}}" aria-expanded="false" aria-controls="collapse{{testId}}" class="link link-danger">
    <span class="label label-danger">{{!nfailedSpan}}</span></a></span>
    <span class="pull-right"><a href="#">+</a> <a href="#">x</a></span><br/><br/>
    <div style="display:none">
        <div class="header editable">{{!testHeader}}</div>
        <div class="comment editable">{{!testComment}}</div>
    </div>
    <div class="collapse" id="collapse{{testId}}">
        <div class="well">
<%
        ids = test['ids']
        for _id in ids:
            ping = group['ids'][_id.__str__()]
            gid = ping.get('gid')
            hid = ping.get('hid')
            print(ping.keys())
            doc = ping.get('doc')
            if doc is not None:
                host = doc.get('host')
                port = doc.get('port')
            else:
                host = "null"
                port = "null"
            end
%>
            <a href="https://mms.mongodb.com/host/detail/{{gid}}/{{hid}}">{{host}}:{{port}}</a></br>
%       end
        </div>
    </div>
        {{failedTs}}: Last noticed<br/>
%       if ticketed is not None:
        {{ticketTs}}: Created <a href="https://jira.mongodb.org/browse/{{ticketKey}}">{{ticketKey}}</a><br/>
%       end
%       if resolved is not None:
        {{resolved.replace(microsecond=0)}}: Issue resolved
%       end
<%
        if type == "resolved":
            pass
        else:
%>
    <br/>
    <div role="group" aria-label="buttons">
        <button type="button" class="btn btn-default">Ignore forever</button>
        <button type="button" class="btn btn-default" onclick="addToTicket(this, '{{!testId}}')">Add to ticket</button>
    </div>
%       end
</div>
    <%
    end
end
%>

<div class="container-fluid">
    <div class="row">
        <div class="col-lg-12">
            <h1>{{group['name']}} <small><a href="https://mms.mongodb.com/host/list/{{group['_id']}}">MMS</a></small></h1>
        </div>
    </div>
    <div class="row">
        <div class="col-lg-12">
<%
if group['company'] is not None:
    if 'sales' in group['company'] and len(group['company']['sales']) > 0:
        salesrep = group['company']['sales'][0]['jira']
    else:
        salesrep = None
    end

    sf_account_id = group['company'].get('sf_account_id')
    sf_project_id = group['company'].get('sf_project_id')
end
%>
            <strong>Salesforce:</strong> <a href="https://mongodb.my.salesforce.com/{{sf_account_id}}">Account</a>,
            <a href="https://mongodb.my.salesforce.com/{{sf_project_id}}">Project</a>
            &nbsp;<strong>Sales Rep:</strong> <a href="https://corp.10gen.com/employees/{{salesrep}}">{{salesrep}}</a>
        </div>
    </div>
    <hr/>
    <div class="row">
        <div class="col-lg-6" style="overflow: hidden;">
            <h4>Proactive Ticket Draft</h4>
            <div id="div_ticket" class="well well-sm">
                <div id="div_ticketSummary">
                    <h4>Summary:</h4>
                    <div class="editable">
                        MongoDB Proactive: Issues identified in MMS
                    </div>
                </div>
                <div id="div_ticketDescription">
                    <h4>Description:</h4>
                    <div class="editable">
                        {{testDescriptionCache.get('greeting')}},
                    </div><br/>
                    <div class="editable">
                        {{testDescriptionCache.get('opening')}}
                    </div><br/>
                    <div id="div_ticketDescription_mainBody"></div>
                    <div class="editable">
                        {{!testDescriptionCache.get('closing')}}
                    </div><br/>
                    <div class="editable">
                        {{!testDescriptionCache.get('signoff')}}
                    </div>
                </div>
            </div>
            <div class="pull-right">
                <a class="btn btn-primary" href="#">Create Ticket</a>
            </div>
        </div>
        <div class="col-lg-6">
            <span class="h4 pull-right">Failed Tests</span>
            <ul id="myTab" class="nav nav-tabs" role="tablist">
                <li role="presentation" class="active"><a href="#failed" id="failed-tab" role="tab" data-toggle="tab" aria-controls="failed" aria-expanded="true">Not Ticketed ({{getNTests('failed')}})</a></li>
                <li role="presentation"><a href="#ticketed" id="ticketed-tab" role="tab" data-toggle="tab" aria-controls="ticketed" aria-expanded="true">Ticketed ({{getNTests('ticketed')}})</a></li>
                <li role="presentation"><a href="#resolved" id="resolved-tab" role="tab" data-toggle="tab" aria-controls="resolved" aria-expanded="true">Resolved ({{getNTests('resolved')}})</a></li>
            </ul><br/>
            <div class="tab-content">
                <div role="tabpanel" class="tab-pane active" id="failed" aria-labelledBy="failed-tab">
%                   showTests('failed')
                </div>
                <div role="tabpanel" class="tab-pane" id="ticketed" aria-labelledBy="ticketed-tab">
%                   showTests('ticketed')
                </div>
                <div role="tabpanel" class="tab-pane" id="resolved" aria-labelledBy="resolved-tab">
%                   showTests('resolved')
                </div>
            </div>
        </div>
    </div>
</div>

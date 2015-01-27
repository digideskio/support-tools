<%
def showFailedTests(src=None):
    for test in group['failedTests']:
        if src is None or src == test['src']:
            testName = test['test']
            testSrc = test['src']
            testComment = testDescriptionCache[testSrc][testName]['comment']
            testHeader = testDescriptionCache[testSrc][testName]['header']
            testId = test['_id']
            testIgnore = test.get('ignore', None)
            testNids = test['nids']
    %>
<div id="div_failedTests_{{testSrc}}_{{testName}}", class="well well-sm">
<%
            if testSrc == 'pings':
                nfailedSpan = "(%s)" % testNids
            else:
                nfailedSpan = ""
            end
%>
    <span class="h4">{{!testName}} {{!nfailedSpan}}</span><span class="pull-right"><a href="#">+</a> <a href="#">x</a></span><br/><br/>
    <div style="display:none">
        <div class="header editable">{{!testHeader}}</div>
        <div class="comment editable">{{!testComment}}</div>
    </div>
    <div role="group" aria-label="buttons">
        <button type="button" class="btn btn-default">Ignore forever</button>
        <button type="button" class="btn btn-default" onclick="addToTicket(this, '{{!testSrc}}', '{{!testName}}', '{{!testHeader}}', '{{testComment}}')">Add to ticket</button>
    </div>
</div>
    <%
        end
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
            <strong>Sales Rep:</strong> <a href="https://corp.10gen.com/employees/{{group['company']['sales'][0]['jira']}}">{{group['company']['sales'][0]['jira']}}</a>
        </div>
    </div>
    <hr/>
    <div class="row">
        <div class="col-lg-6">
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
                <li role="presentation"><a href="#mmsgroupreports" id="mmsgroupreports-tab" role="tab" data-toggle="tab" aria-controls="mmsgroupreports" aria-expanded="true">MMS Group Reports ({{len(testDescriptionCache['mmsgroupreports'])}})</a></li>
                <li role="presentation" class="active"><a href="#pings" id="pings-tab" role="tab" data-toggle="tab" aria-controls="pings" aria-expanded="true">Pings ({{len(testDescriptionCache['pings'])}})</a></li>
            </ul><br/>
            <div class="tab-content">
                <div role="tabpanel" class="tab-pane" id="mmsgroupreports" aria-labelledBy="mmsgroupreports-tab">
%                   showFailedTests('mmsgroupreports')
                </div>
                <div role="tabpanel" class="tab-pane active" id="pings" aria-labelledBy="pings-tab">
%                   showFailedTests('pings')
                </div>
            </div>
        </div>
    </div>
</div>

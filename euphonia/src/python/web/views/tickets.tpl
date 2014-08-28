<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Support Issue Workflows</h1>
        </div>
    </div>
    <div class="row">
        <div class="panel-group" id="accordion">
            <%
                if ticketWorkflows is not None:
                    for workflow in ticketWorkflows:
                        previous = ""
                        try:
                            previous = ','.join(workflow['prereqs']) + " --> "
                        except:
                            previous = ""
                        end
            %>
                        <div class="panel panel-default">
                            <div class="panel-heading">
                                <h4 class="panel-title"><span style="color:#aaaaaa;">{{previous}}</span>{{workflow['name']}}
                                    <span class="pull-right">
                                        <a class="btn btn-primary" href="/workflow/{{workflow['name']}}/approve">Approve all</a>
                                        <div class="btn-group">
                                            <button type="button" class="btn btn-warning dropdown-toggle" data-toggle="dropdown">Delay All <span class="caret"></span></button>
                                            <ul class="dropdown-menu" role="menu">
                                                <li><a href="/workflow/{{workflow['name']}}/delay/1">Delay 1 Day</a></li>
                                                <li><a href="/workflow/{{workflow['name']}}/delay/3">Delay 3 Days</a></li>
                                                <li><a href="/workflow/{{workflow['name']}}/delay/7">Delay 1 Week</a></li>
                                            </ul>
                                        </div>
                                        <a class="btn btn-danger" href="/workflow/{{workflow['name']}}/remove">Remove All</a>
                                    </span>
                                </h4>
                            </div>
                            <div id="collapseOne" class="panel-collapse collapse">
                                <div class="panel-body">
                                    <div class="col col-lg-12 col-md-12">
                                        <div class="topissues">
                                            <table class="table table-striped">
                                                <thead>
                                                    <tr>
                                                        <th>Ticket</th>
                                                        <th>Approved</th>
                                                        <th>In Progress</th>
                                                        <th>Sleep</th>
                                                        <th>Last Update</th>
                                                        <th>Action</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                <%
                                                for ticket in ticketSummary:
                                                    if ticket['workflow'] == workflow['name']:
                                                        issue = issues[str(ticket['iid'])]
                                                        sleep = ""
                                                        try:
                                                            sleep = issue['karakuri']['sleep']
                                                        except:
                                                            sleep = ""
                                                        end
                                                %>
                                                        <tr>
                                                            <td><a href="{{issue['jira']['self']}}">{{issue['jira']['key']}}</a></td>
                                                            <td>{{ticket['approved']}}</td>
                                                            <td>{{ticket['inProg']}}</td>
                                                            <td>{{sleep}}</td>
                                                            <td>{{ticket['t']}}</td>
                                                            <td>
                                                                <%
                                                                disabled = ""
                                                                if ticket['approved'] == True:
                                                                    disabled = " disabled"
                                                                end
                                                                %>
                                                                <a class="btn btn-primary{{disabled}}" href="/ticket/{{ticket['iid']}}/approve">Approve</a>
                                                                <div class="btn-group">
                                                                    <button type="button" class="btn btn-warning dropdown-toggle" data-toggle="dropdown">Delay <span class="caret"></span></button>
                                                                    <ul class="dropdown-menu" role="menu">
                                                                        <li><a href="/ticket/{{ticket['iid']}}/delay/1">Delay 1 Day</a></li>
                                                                        <li><a href="/ticket/{{ticket['iid']}}/delay/3">Delay 3 Days</a></li>
                                                                        <li><a href="/ticket/{{ticket['iid']}}/delay/7">Delay 1 Week</a></li>
                                                                    </ul>
                                                                </div>
                                                                <a class="btn btn-danger" href="/ticket/{{ticket['iid']}}/remove">Remove</a>
                                                            </td>
                                                        </tr>
                                                <%
                                                    end
                                                end
                                                %>
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
            %   end
        </div>
    </div>
</div>
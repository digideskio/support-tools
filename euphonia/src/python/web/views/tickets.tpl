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
                                <div class="pull-right">
                                    <a class="btn btn-primary" href="/workflow/{{workflow['name']}}/approve">Approve All</a>
                                    <div class="btn-group">
                                        <button type="button" class="btn btn-warning dropdown-toggle" data-toggle="dropdown">Sleep All <span class="caret"></span></button>
                                        <ul class="dropdown-menu" role="menu">
                                            <li><a href="/workflow/{{workflow['name']}}/sleep/1">Sleep 1 Day</a></li>
                                            <li><a href="/workflow/{{workflow['name']}}/sleep/3">Sleep 3 Days</a></li>
                                            <li><a href="/workflow/{{workflow['name']}}/sleep/7">Sleep 1 Week</a></li>
                                        </ul>
                                    </div>
                                    <a class="btn btn-danger" href="/workflow/{{workflow['name']}}/remove">Remove All</a>
                                </div>
                            </h4>
                            <div style="clear:both"></div>
                        </div>
                        <div class="panel-body">
                            <div class="col col-lg-12 col-md-12">
                                <div class="topissues">
                                    <table class="table table-striped">
                                        <thead>
                                            <tr>
                                                <th>Ticket</th>
                                                <th>Approved</th>
                                                <th>In Progress</th>
                                                <th>Done</th>
                                                <th>Start</th>
                                                <th>Properties</th>
                                                <th><span class="pull-right">Action</span></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                        <%
                                        for ticket in ticketSummary:
                                            if ticket['workflow'] == workflow['name']:
                                                issue = issues[str(ticket['iid'])]
                                                doneDisabled = False
                                                if 'done' in ticket:
                                                    doneDisabled = ticket['done']
                                                end
                                                if doneDisabled:
                                                    doneDisabled = "disabled"
                                                else:
                                                    doneDisabled = ""
                                                end
                                        %>
                                                <tr>
                                                    <td><a target="_blank" href="http://jira.mongodb.org/browse/{{issue['key']}}">{{issue['key']}}</a></td>
                                                    <td>{{ticket['approved']}}</td>
                                                    <td>{{ticket['inProg']}}</td>
                                                    <td>{{ticket['done']}}</td>
                                                    <td>{{ticket['startDate']}}</td>
                                                    <td>
                                                        <i class="glyphicon glyphicon-time metadata" data-toggle="tooltip" data-placement="top" title="Last Updated: {{ticket['updateDate']}}"></i>
                                                        % if ticket['removed'] == True:
                                                        <i class="glyphicon glyphicon-remove metadata" data-toggle="tooltip" data-placement="top" title="Removed {{ticket['updateDate']}}"></i>
                                                        % end
                                                        % if ticket['done'] == True:
	                                                        <i class="glyphicon glyphicon-ok metadata" data-toggle="tooltip" data-placement="top" title="Done {{ticket['updateDate']}}"></i>
	                                                    % end
                                                    </td>
                                                    <td>
                                                        <div class="pull-right">
                                                        % if ticket['approved'] == True:
                                                            <a class="btn btn-info" href="/ticket/{{ticket['_id']}}/disapprove">Disapprove</a>
                                                        % else:
                                                            <a class="btn btn-primary" href="/ticket/{{ticket['_id']}}/approve">Approve</a>
                                                        % end
                                                        <div class="btn-group">
                                                            <button type="button" class="btn btn-warning dropdown-toggle" data-toggle="dropdown">Sleep <span class="caret"></span></button>
                                                            <ul class="dropdown-menu" role="menu">
                                                                <li><a href="/ticket/{{ticket['_id']}}/sleep/1">Sleep 1 Day</a></li>
                                                                <li><a href="/ticket/{{ticket['_id']}}/sleep/3">Sleep 3 Days</a></li>
                                                                <li><a href="/ticket/{{ticket['_id']}}/sleep/7">Sleep 1 Week</a></li>
                                                            </ul>
                                                        </div>
                                                        <a class="btn btn-danger {{doneDisabled}}" href="/ticket/{{ticket['_id']}}/remove">Remove</a>
                                                        </div>
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
            <%
                    end
                end
            %>
        </div>
    </div>
</div>
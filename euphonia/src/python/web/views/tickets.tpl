<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Support Issue Workflows</h1>
        </div>
    </div>
    <div class="row">
        <div id="ticketList" class="col-lg-12">
            <div class="panel-group" id="accordion">
            <%
                if len(ticketWorkflows) > 0:
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
                                    <a class="btn btn-primary metadata" data-toggle="tooltip" data-placement="top" title="Process All" href="/workflow/{{workflow['name']}}/process"><i class="glyphicon glyphicon-play-circle"></i></a>
                                    <a class="btn btn-success metadata" data-toggle="tooltip" data-placement="top" title="Approve All" href="/workflow/{{workflow['name']}}/approve"><i class="glyphicon glyphicon-ok"></i></a>
                                    <i class="metadata" data-toggle="tooltip" data-placement="top" title="Sleep All">
                                        <div class="btn-group">
                                            <button type="button" class="btn btn-warning dropdown-toggle" data-toggle="dropdown"><i class="glyphicon glyphicon-time"></i>&nbsp;<span class="caret"></span></button>
                                            <ul class="dropdown-menu dropdown-menu-right" role="menu">
                                                <li><a href="/workflow/{{workflow['name']}}/wake">Wake All!</a></li>
                                                <li><a href="/workflow/{{workflow['name']}}/sleep/86400">Sleep 1 Day</a></li>
                                                <li><a href="/workflow/{{workflow['name']}}/sleep/259200">Sleep 3 Days</a></li>
                                                <li><a href="/workflow/{{workflow['name']}}/sleep/604800">Sleep 1 Week</a></li>
                                            </ul>
                                        </div>
                                    </i>
                                    <a class="btn btn-danger metadata" data-toggle="tooltip" data-placement="top" title="Remove All" href="/workflow/{{workflow['name']}}/remove"><i class="glyphicon glyphicon-trash"></i></a>
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
                                                <th>Start</th>
                                                <th>Status</th>
                                                <th><span class="pull-right">Actions</span></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                        <%
                                        for ticket in ticketSummary:
                                            print ticket
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
                                                    <td><a href="javascript:void(0);" onclick="showPage(this,'http://jira.mongodb.org/browse/{{issue['key']}}','{{issue['key']}}');">{{issue['key']}}</a></td>
                                                    <td>{{ticket['startDate']}}</td>
                                                    <td>
                                                        <i class="glyphicon glyphicon-time metadata" data-toggle="tooltip" data-placement="top" title="Last Updated: {{ticket['updateDate']}}"></i>
                                                        % if ticket['removed'] == True:
                                                            <i class="glyphicon glyphicon-trash metadata" data-toggle="tooltip" data-placement="top" title="Removed: {{ticket['updateDate']}}"></i>
                                                        % elif ticket['done'] == True:
	                                                        <i class="glyphicon glyphicon-ok metadata" data-toggle="tooltip" data-placement="top" title="Done: {{ticket['updateDate']}}"></i>
	                                                    % elif ticket['inProg'] == True:
                                                            <i class="glyphicon glyphicon-refresh metadata" data-toggle="tooltip" data-placement="top" title="In Progress since: {{ticket['updateDate']}}"></i>
                                                        % elif ticket['approved'] == True:
                                                            <i class="glyphicon glyphicon-thumbs-up metadata" data-toggle="tooltip" data-placement="top" title="Approved, not Done since: {{ticket['updateDate']}}"></i>
                                                        % end
                                                    </td>
                                                    <td>
                                                        <div class="pull-right">
                                                            <a class="btn btn-xs btn-primary metadata {{doneDisabled}}" data-toggle="tooltip" data-placement="top" title="Process" href="/ticket/{{ticket['_id']}}/process"><i class="glyphicon glyphicon-play"></i></a>
                                                        % if ticket['approved'] == True:
                                                            <a class="btn btn-xs btn-default metadata {{doneDisabled}}" data-toggle="tooltip" data-placement="top" title="Disapprove" href="/ticket/{{ticket['_id']}}/disapprove"><i class="glyphicon glyphicon-ok"></i></a>
                                                        % else:
                                                            <a class="btn btn-xs btn-success metadata {{doneDisabled}}" data-toggle="tooltip" data-placement="top" title="Approve" href="/ticket/{{ticket['_id']}}/approve"><i class="glyphicon glyphicon-ok"></i></a>
                                                        % end
                                                        <i class="metadata" data-toggle="tooltip" data-placement="top" title="Sleep">
                                                            <div class="btn-group">
                                                                <button type="button" class="btn btn-xs btn-warning dropdown-toggle {{doneDisabled}}" data-toggle="dropdown"><i class="glyphicon glyphicon-time"></i>&nbsp;<span class="caret"></span></button>
                                                                <ul class="dropdown-menu dropdown-menu-right {{doneDisabled}}" role="menu">
                                                                    <li><a href="/ticket/{{ticket['_id']}}/wake">Wake Up!</a></li>
                                                                    <li><a href="/ticket/{{ticket['_id']}}/sleep/86400">Sleep 1 Day</a></li>
                                                                    <li><a href="/ticket/{{ticket['_id']}}/sleep/259200">Sleep 3 Days</a></li>
                                                                    <li><a href="/ticket/{{ticket['_id']}}/sleep/604800">Sleep 1 Week</a></li>
                                                                </ul>
                                                            </div>
                                                        </i>
                                                        <a class="btn btn-xs btn-danger metadata {{doneDisabled}}" data-toggle="tooltip" data-placement="top" title="Remove" href="/ticket/{{ticket['_id']}}/remove"><i class="glyphicon glyphicon-trash"></i></a>
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
        <div id="ticketContent" style="display:none">
            <div class="panel-group" id="accordion">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 id="ticketTitle" class="panel-title">
                            <span></span>
                            <div class="pull-right">
                                <a target="_blank" id="ticketLink" href=""><i class="glyphicon glyphicon-share"></i></a>
                                <a href="javascript:void(0);" onclick="closePage();"><i class="glyphicon glyphicon-remove"></i></a>
                            </div>
                        </h4>
                        <div style="clear:both"></div>
                    </div>
                    <div class="panel-body">
                        <iframe src="" id="ticketFrame"></iframe>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
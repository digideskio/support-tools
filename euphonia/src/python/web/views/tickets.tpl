<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Support Issue Workflows</h1>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-12 col-md-12">
            <div class="topissues">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Ticket</th>
                            <th>Workflow</th>
                            <th>Approved</th>
                            <th>In Progress</th>
                            <th>Last Update</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                    % for ticket in ticketSummary['tickets']:
                    %   issue = issues[str(ticket['iid'])]
                        <tr>
                            <td><a href="{{issue['self']}}">{{issue['key']}}</a></td>
                            <td>{{ticket['workflow']}}</td>
                            <td>{{ticket['approved']}}</td>
                            <td>{{ticket['inProg']}}</td>
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
                                    <button type="button" class="btn btn-danger dropdown-toggle" data-toggle="dropdown">Delay <span class="caret"></span></button>
                                    <ul class="dropdown-menu" role="menu">
                                        <li><a href="/ticket/{{ticket['iid']}}/delay/1">Delay 1 Day</a></li>
                                        <li><a href="/ticket/{{ticket['iid']}}/delay/3">Delay 3 Days</a></li>
                                        <li><a href="/ticket/{{ticket['iid']}}/delay/7">Delay 1 Week</a></li>
                                    </ul>
</div>
                            </td>
                        </tr>
                    % end
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
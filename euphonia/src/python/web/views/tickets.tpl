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
                        <tr>
                            <td>{{ticket['iid']}}</td>
                            <td>{{ticket['workflow']}}</td>
                            <td>{{ticket['approved']}}</td>
                            <td>{{ticket['inProg']}}</td>
                            <td>{{ticket['t']}}</td>
                            <td>
                                <button class="btn btn-primary" onclick="alert('Approving ticket {{ticket['iid']}}');">Approve</button>
                                <div class="btn-group">
                                    <button type="button" class="btn btn-danger dropdown-toggle" data-toggle="dropdown">Delay <span class="caret"></span></button>
                                    <ul class="dropdown-menu" role="menu">
                                        <li><a href="#" onclick="alert('Delaying ticket {{ticket['iid']}} for 1 day');">Delay 1 Day</a></li>
                                        <li><a href="#" onclick="alert('Delaying ticket {{ticket['iid']}} for 3 days');">Delay 3 Days</a></li>
                                        <li><a href="#" onclick="alert('Delaying ticket {{ticket['iid']}} for 1 week');">Delay 1 Week</a></li>
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
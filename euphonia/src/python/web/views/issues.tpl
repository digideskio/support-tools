<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Issue Summary</h1>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-12 col-md-12">
            <div class="progress">
                % priorities = [{'low':'success'},{'medium':'warning'},{'high':'danger'}]
                % for item in priorities:
                %   priority = item.keys()[0]
                    <div class="progress-bar progress-bar-{{item[priority]}}" style="width:{{float(float(issueSummary[priority])/float(issueSummary['total']))*100}}%" role="progress-bar" data-toggle="tooltip" data-placement="top" title="{{priority}}: {{issueSummary[priority]}}">
                    </div>
                % end
            </div>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-6 col-md-6">
            <div class="topissues">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Issue</th>
                            <th>Count</th>
                        </tr>
                    </thead>
                    <tbody>
                    % for issue in topIssues:
                        <tr><td><a href="/issue/{{issue['_id']}}">{{issue['_id']}}</a></td><td>{{issue['failedCount']}}</td></tr>
                    % end
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
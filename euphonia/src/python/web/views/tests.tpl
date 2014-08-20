<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Test Summary</h1>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-12 col-md-12">
            <div class="progress">
                % priorities = [{'low':'success'},{'medium':'warning'},{'high':'danger'}]
                % for item in priorities:
                %   priority = item.keys()[0]
                    <div class="progress-bar progress-bar-{{item[priority]}}" style="width:{{float(float(testSummary[priority])/float(testSummary['total']))*100}}%" role="progress-bar" data-toggle="tooltip" data-placement="top" title="{{priority}}: {{testSummary[priority]}}">
                    </div>
                % end
            </div>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-6 col-md-6">
            <div class="toptests">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Test</th>
                            <th>Count</th>
                        </tr>
                    </thead>
                    <tbody>
                    % for test in topTests:
                        <tr><td><a href="/test/{{test['_id']}}">{{test['_id']}}</a></td><td><b>{{test['failedCount']}}</b></td></tr>
                    % end
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
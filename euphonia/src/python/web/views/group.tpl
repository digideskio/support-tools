<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            % cType = "Free"
            % if group[0]['IsCsCustomer'] == True:
            %   cType = "CS"
            <h1>{{group[0]['GroupName']}} <small><i>({{cType}})</i></small></h1>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-12">
            % cType = "Free"
            % if group[0]['IsCsCustomer'] == True:
            %   cType = "CS"
            <span><strong>Contact:</strong> <a href="mailto:{{group[0]['UserEmail']}}">{{group[0]['FirstName']}} {{group[0]['LastName']}}</a></span>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-6 col-md-6">
            <h4>Summary</h4>
            <pre>
                % for dataPoint in group:
                %   for key in dataPoint:
                    {{key}}: {{dataPoint[key]}}
                %   end
                % end
            </pre>
        </div>
        % issueDesc = "an issue"
        % if(group[0]['numFailedTests'] > 1):
        %   issueDesc = "issues"
        % end
        <div class="col col-lg-6 col-md-6">
            % for test in group[0]['failedTests']:
            %   testDescription = descriptionCache.get(test)
            %   if testDescription != None:
                 <div class="col col-lg-12">
                    <h4>{{test}}</h4>
                    <pre>
{{descriptionCache.get('greeting')}} {{group[0]['FirstName']}},

{{descriptionCache.get('opening')}}

{{testDescription}}

{{descriptionCache.get('closing')}}
                    </pre>
                    <div class="pull-right">
                        <a class="btn btn-primary" href="#">Create Jira Issue</a>
                    </div>
                 </div>
            %   end
            % end
        </div>
    </div>
</div>
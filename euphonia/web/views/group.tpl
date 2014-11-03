<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            % cType = "Free"
            % if group['IsCsCustomer'] == True:
            %   cType = "CS"
            <h1>{{group['GroupName']}} <small><i>({{cType}})</i></small></h1>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-12">
            % cType = "Free"
            % if group['IsCsCustomer'] == True:
            %   cType = "CS"
            <span><strong>Contact:</strong> <a href="mailto:{{group['UserEmail']}}">{{group['FirstName']}} {{group['LastName']}}</a></span>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-4 col-md-4">
            <h4>Summary</h4>
            <pre>
            %   for key in group:
{{key}}: {{group[key]}}
            %   end
            </pre>
        </div>
        <div class="col col-lg-8 col-md-8">
            <div class="col col-lg-12">
                <h4>Customer Email</h4>
                <div class="well">
                    {{descriptionCache.get('greeting')}} {{group['FirstName']}},<br/>
                    <br/>
                    {{descriptionCache.get('opening')}}<br/>
                    <br/>
                    <ul>
                    <%
                    for test in group['failedTests']:
                        testName = test.get('test')
                        testIgnore = test.get('ignore')
                        testDescription = descriptionCache.get(testName)
                        if testDescription != None and testIgnore == 0:
                    %>
                        <li>{{!testDescription}}</li><br/>
                    <%
                        end
                    end
                    %>
                    </ul>
                    {{!descriptionCache.get('closing')}}
                </div>
            </div>
            % for test in group['failedTests']:
            %   testName = test.get('test')
            %   testIgnore = test.get('ignore')
            %   testDescription = descriptionCache.get(testName)
            %   if testDescription != None:
                 <div class="col col-lg-12">
                    <h4>{{testName}}</h4>
                    <div class="well">
                    {{descriptionCache.get('greeting')}} {{group['FirstName']}},<br/>
                    <br/>
                    {{!testDescription}}
                    </div>
                    <div class="pull-right btn-group">
                        <a class="btn btn-danger {{"disabled" if testIgnore == 1 else ""}}" href="/group/{{group['GroupId']}}/ignore/{{testName}}">Ignore Issue</a>
                        <a class="btn btn-success {{"disabled" if testIgnore == 0 else ""}}" href="/group/{{group['GroupId']}}/include/{{testName}}">Include Issue</a>
                    </div>
                 </div>
            %   end
            % end
            <div class="col col-lg-12 col-md-12">
                <br/>
                <br/>
                <div class="pull-right">
                    <a class="btn btn-primary" href="#">Send Email</a>
                </div>
            </div>
        </div>
    </div>
</div>
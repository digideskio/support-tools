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
        <div class="col col-lg-12">
            <pre>
                % for dataPoint in group:
                %   for key in dataPoint:
                    {{key}}: {{dataPoint[key]}}
                %   end
                % end
            </pre>
        </div>
    </div>
</div>
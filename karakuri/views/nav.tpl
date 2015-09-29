<nav class="navbar navbar-default" role="navigation">
    <div class="container-fluid">
        <div class="navbar-header">
            <button type="button" class="navbar-toggle" data-toggle="collapse" data-target="#bs-example-navbar-collapse-1">
                <span class="sr-only">Toggle navigation</span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
            </button>
            <a style="font-family:'Trebuchet';text-decoration:none;font-size: 2.0em; padding: 5px 5px;" class="navbar-brand" href="/"><img style="width:40px;height:40px;" src="/static/logo.png"/>&nbsp;<span style="color:#522900;">karakuri</span><span style="color:#CCCCB2">DB</span></a>
        </div>
        <div class="collapse navbar-collapse">
            <ul class="nav navbar-nav">
            <%
            for section in ["workflows"]:
                active = ""
                if section == renderpage:
                    active = "active"
                end
            %>
                <li><a href="/{{section}}" class="{{active}}">{{section}}</a></li>
            % end
            </ul>
        </div>
    </div>
</nav>
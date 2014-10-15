<nav class="navbar navbar-default" role="navigation">
    <div class="container-fluid">
        <div class="navbar-header">
            <button type="button" class="navbar-toggle" data-toggle="collapse" data-target="#bs-example-navbar-collapse-1">
                <span class="sr-only">Toggle navigation</span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
            </button>
            <a style="font-family:'Trebuchet';text-decoration:none;font-size: 2.0em; padding: 5px 5px;" class="navbar-brand" href="/"><img style="width:40px;height:40px;" src="/img/logo.png"/>&nbsp;<span style="color:#522900;">proactive</span><span style="color:#CCCCB2">DB</span></a>
        </div>
        <div class="collapse navbar-collapse">
            <ul class="nav navbar-nav">
            <%
            for section in ["groups","tests","workflows","issues"]:
                active = ""
                if section == renderpage:
                    active = "active"
                end
            %>
                <li><a href="/{{section}}" class="{{active}}">{{section}}</a></li>
            % end
            </ul>
            <ul class="nav navbar-nav navbar-right">
                <li>
                    <form class="navbar-form" role="search">
                        <div id="searchBox" class="form-group has-feedback" style="width:300px;">
                            <input id="groupSearch" type="text" class="form-control" style="box-shadow: none; width:100%;" autocomplete="off" placeholder=""/>
                            <i class="glyphicon glyphicon-search form-control-feedback"></i>
                        </div>
                    </form>
                </li>
                <li><a href="#"><span class="glyphicon glyphicon-user"></span></a></li>
            </ul>
        </div>
    </div>
</nav>
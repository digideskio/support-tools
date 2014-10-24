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
                                    <a class="btn btn-success metadata" data-toggle="tooltip" data-placement="top" title="Approve All" href="/workflow/{{workflow['name']}}/approve"><i class="glyphicon glyphicon-ok"></i></a>
                                    <i class="metadata" data-toggle="tooltip" data-placement="top" title="Sleep All">
                                        <div class="btn-group">
                                            <button type="button" class="btn btn-warning dropdown-toggle" data-toggle="dropdown"><i class="glyphicon glyphicon-time"></i>&nbsp;<span class="caret"></span></button>
                                            <ul class="dropdown-menu dropdown-menu-right" role="menu">
                                                <li><a href="/workflow/{{workflow['name']}}/wake">Wake All!</a></li>
                                                <li><a href="/workflow/{{workflow['name']}}/sleep/86400">Sleep 1 Day</a></li>
                                                <li><a href="/workflow/{{workflow['name']}}/sleep/259200">Sleep 3 Days</a></li>
                                                <li><a href="/workflow/{{workflow['name']}}/sleep/604800">Sleep 1 Week</a></li>
                                                <li><a href="/workflow/{{workflow['name']}}/sleep/604800">Freeze</a></li>
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
                                            if ticket['workflow'] == workflow['name'] and str(ticket['iid']) in issues:
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
                                                if ticket['frozen'] == True:
                                                    hidden = "class=frozen style=display:none"
                                                else:
                                                    hidden = ""
                                                end
                                        %>
                                                <tr id="{{ticket['_id']}}" {{hidden}}>
                                                    <td><a href="javascript:void(0);" onclick="showPage(this,'http://jira.mongodb.org/browse/{{issue['key']}}','{{issue['key']}}');">{{issue['key']}}</a></td>
                                                    <td class="startdate">{{ticket['startDate']}}</td>
                                                    <td>
                                                        <i id="{{ticket['_id']}}-time" class="glyphicon glyphicon-time metadata" data-toggle="tooltip" data-placement="top" title="Last Updated: {{ticket['updateDate']}}"></i>
                                                        <%
                                                            hidden = "display:none"
                                                            if ticket['frozen'] == True:
                                                                hidden = ""
                                                            end
                                                        %>
                                                        <i id="{{ticket['_id']}}-frozen" class="glyphicon glyphicon-certificate metadata stats" style="{{hidden}}" data-toggle="tooltip" data-placement="top" title="Frozen"></i>
                                                        <%
                                                            hidden = "display:none"
                                                            if ticket['done'] == True:
                                                                hidden = ""
                                                            end
                                                        %>
	                                                    <i id="{{ticket['_id']}}-done" class="glyphicon glyphicon-ok metadata stats" style="{{hidden}}" data-toggle="tooltip" data-placement="top" title="Done"></i>
	                                                    <%
                                                            hidden = "display:none"
                                                            if ticket['inProg'] == True:
                                                                hidden = ""
                                                            end
                                                        %>
                                                        <i id="{{ticket['_id']}}-inprogress" class="glyphicon glyphicon-refresh metadata stats" style="{{hidden}}" data-toggle="tooltip" data-placement="top" title="In Progress"></i>
                                                        <%
                                                            hidden = "display:none"
                                                            if ticket['approved'] == True and ticket['done'] == False:
                                                                hidden = ""
                                                            end
                                                        %>
                                                        <i id="{{ticket['_id']}}-approve" class="glyphicon glyphicon-thumbs-up metadata stats" style="{{hidden}}" data-toggle="tooltip" data-placement="top" title="Approved, not Done"></i>
                                                    </td>
                                                    <td>
                                                        <div class="pull-right">
                                                        <%
                                                            hidden = "display:none"
                                                            if ticket['approved'] == True:
                                                                hidden = ""
                                                            end
                                                        %>
                                                            <a id="{{ticket['_id']}}-approve-btn" class="btn btn-xs btn-default metadata approve {{doneDisabled}}" style="{{hidden}}" data-toggle="tooltip" data-placement="top" title="Disapprove" href="javascript:void(0);" onclick="disapproveTask('{{ticket['_id']}}');"><i class="glyphicon glyphicon-ok"></i></a>
                                                        <%
                                                            hidden = "display:none"
                                                            if ticket['approved'] == False:
                                                                hidden = ""
                                                            end
                                                        %>
                                                            <a id="{{ticket['_id']}}-approve-btn" class="btn btn-xs btn-success metadata approve {{doneDisabled}}" style="{{hidden}}" data-toggle="tooltip" data-placement="top" title="Approve" href="javascript:void(0);" onclick="approveTask('{{ticket['_id']}}');"><i class="glyphicon glyphicon-ok"></i></a>
                                                        <i class="metadata" data-toggle="tooltip" data-placement="top" title="Sleep">
                                                            <div class="btn-group">
                                                                <button type="button" class="btn btn-xs btn-warning dropdown-toggle {{doneDisabled}}" data-toggle="dropdown"><i class="glyphicon glyphicon-time"></i>&nbsp;<span class="caret"></span></button>
                                                                <ul class="dropdown-menu dropdown-menu-right {{doneDisabled}}" role="menu">
                                                                    <li><a href="javascript:void(0);" onclick="wakeTask('{{ticket['_id']}}');">Wake Up!</a></li>
                                                                    <li><a href="javascript:void(0);" onclick="sleepTask('{{ticket['_id']}}',86400);">Sleep 1 Day</a></li>
                                                                    <li><a href="javascript:void(0);" onclick="sleepTask('{{ticket['_id']}}',259200);">Sleep 3 Days</a></li>
                                                                    <li><a href="javascript:void(0);" onclick="sleepTask('{{ticket['_id']}}',604800);">Sleep 1 Week</a></li>
                                                                    <li><a href="javascript:void(0);" onclick="sleepTask('{{ticket['_id']}}');">Freeze</a></li>
                                                                </ul>
                                                            </div>
                                                        </i>
                                                        <a class="btn btn-xs btn-danger metadata {{doneDisabled}}" data-toggle="tooltip" data-placement="top" title="Remove" href="javascript:void(0);" onclick="removeTask('{{ticket['_id']}}');"><i class="glyphicon glyphicon-trash"></i></a>
                                                        </div>
                                                    </td>
                                                </tr>
                                        <%
                                            elif ticket['workflow'] == workflow['name'] and str(ticket['iid']) not in issues:
                                        %>
                                                <tr id="{{ticket['_id']}}"><td colspan="4" class="bg-danger">Ticket {{ticket['_id']}} not found</td></tr>
                                        <%
                                            end
                                        end
                                        %>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                        <div class="panel-footer">
                            <div class="pull-right"><a href="javascript:void(0);" onclick="$(this).closest('.panel').find('.frozen').toggle(400);">Show/Hide Frozen Tasks</a></div>
                            <div style="clear:both"></div>
                        </div>
                    </div>
                    <br/>
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
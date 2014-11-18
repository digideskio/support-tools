% workflow = data['data']['workflow']
% ticketSummary = data['ticketSummary']
% issues = data['issues']
% hide_done = data['hide_done']
% hide_frozen = data['hide_frozen']
<div id="{{workflow['name']}}" class="panel panel-default div_workflow">
<form class="form_workflow">
    <div class="panel-heading">
        <div class="pull-left">
            <span class="h4 pull-left" style="margin-right:1em">{{workflow['name']}}</span>
        </div>
        <div class="pull-right">
            <a class="btn btn-success metadata" data-toggle="tooltip" data-placement="top" title="Approve" href="javascript:void(0);" onclick="approveTasks(this);"><i class="glyphicon glyphicon-ok"></i></a>
            <a class="btn btn-info metadata" data-toggle="tooltip" data-placement="top" title="Disapprove" href="javascript:void(0);" onclick="disapproveTasks(this);"><i class="glyphicon glyphicon-remove"></i></a>
            <i class="metadata" data-toggle="tooltip" data-placement="top" title="Sleep">
                <div class="btn-group">
                    <button type="button" class="btn btn-warning dropdown-toggle" data-toggle="dropdown"><i class="glyphicon glyphicon-time"></i>&nbsp;<span class="caret"></span></button>
                    <ul class="dropdown-menu dropdown-menu-right" role="menu">
                        <li><a href="javascript:void(0);" onclick="wakeTasks(this);">Wake!</a></li>
                        <li><a href="javascript:void(0);" onclick="sleepTasks(this, 86000);">Sleep 1 Day</a></li>
                        <li><a href="javascript:void(0);" onclick="sleepTasks(this, 259200);">Sleep 3 Days</a></li>
                        <li><a href="javascript:void(0)" onclick="sleepTasks(this, 604800);">Sleep 1 Week</a></li>
                        <li><a href="javascript:void(0)" onclick="sleepTasks(this)">Freeze</a></li>
                    </ul>
                </div>
            </i>
            <a class="btn btn-danger metadata" data-toggle="tooltip" data-placement="top" title="Remove" href="javascript:void(0);" onclick="removeTasks(this);"><i class="glyphicon glyphicon-trash"></i></a>
        </div>
        <div style="clear:both"></div>
    </div>
    <div class="panel-body">
        <div class="col col-lg-12 col-md-12">
            <div class="topissues">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th colspan=4>
                                <span id="selectTasksDropdown" class="dropdown">
                                    <input class="inactive" type="checkbox" onclick="toggleSelect(this)">
                                    <a href="javascript:void(0);" id="a_selectTasksDropdown" data-toggle="dropdown"><span class="caret"></span></a>
                                    <ul class="dropdown-menu dropdown-menu-left" role="menu" aria-labelledby="a_selectTasksDropdown">
                                        <li style="margin-left:10px">
                                            <a href="javascript:void(0);" onclick="selectAll(this)">All</a>
                                        </li>
                                        <li style="margin-left:10px">
                                            <a href="javascript:void(0);" onclick="selectNone(this)">None</a>
                                        </li>
                                    </ul>
                                </span>
                            </th>
                            <th colspan="2">
                                <%
                                if hide_frozen == True:
                                    showHideText = "show frozen"
                                else:
                                    showHideText = "hide frozen"
                                end
                                %>
                                <span class="pull-right" style="margin-left:1em"><a href="javascript:void(0);" onclick="showHide(this, 'frozen');">{{showHideText}}</a></span>
                                <%
                                if hide_done == True:
                                    showHideText = "show done"
                                else:
                                    showHideText = "hide done"
                                end
                                %>
                                <span class="pull-right" style="margin-left:1em"><a href="javascript:void(0);" onclick="showHide(this, 'done');">{{showHideText}}</a></span>
                            </th>
                       </tr>
                        <tr>
                            <th></th>
                            <th>Ticket</th>
                            <th>Company</th>
                            <th>Assignee</th>
                            <th>Start</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                    <%
                    tasks = ticketSummary['tasks']
                    if tasks:
                        for task in tasks:
                            if task['workflow'] == workflow['name'] and str(task['iid']) in issues:
                                issue = issues[str(task['iid'])]
                                include('tasks_workflow_task.tpl', task=task, hide_done=hide_done, hide_frozen=hide_frozen)
                            elif task['workflow'] == workflow['name'] and str(task['iid']) not in issues:
                        %>
                                <tr id="{{task['_id']}}"><td colspan="6" class="bg-danger">Task {{task['_id']}} not found</td></tr>
                        <%
                            end
                        end
                    end
                    %>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="panel-footer">
        <div style="clear:both"></div>
    </div>
</form>
</div>

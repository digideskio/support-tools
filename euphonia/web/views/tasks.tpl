<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12" style="margin-bottom:1em">
            <!--span class="h1">Support Issue Workflows</span-->
            <span id="selectWorkflowsDropdown" class="dropdown">
                <a href="javascript:void(0)" id="a_selectWorkflowsDropdown" data-toggle="dropdown">
                    <i id="i_dropdown" class="glyphicon glyphicon-plus-sign"></i>
                </a>
                <ul class="dropdown-menu dropdown-menu-left" role="menu" aria-labelledby="a_selectWorkflowsDropdown">
                    % for workflow in allWorkflows:
                    <li style="margin-left:10px">
                        <input id="checkbox_{{workflow}}" class="selectWorkflowsDropdownCheckbox" type="checkbox" value="{{workflow}}"> {{workflow}}
                    </li>
                    % end
                </ul>
            </span>
        </div>
    </div>
    <div class="row">
        <div id="ticketList" class="col-lg-12" style="width:50%">
            <div class="panel-group" id="accordion">
                {{! content}}
            </div>
        </div>
        <div id="ticketContent" style="display:none; position:absolute; right:10px">
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

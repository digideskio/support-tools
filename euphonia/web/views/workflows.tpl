<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Support Issue Workflows</h1>
        </div>
    </div>
    <div class="row">
        <div class="col-md-2 sidebar well" id="sidebar" role="navigation">
            <h4>Existing Workflows</h4>
            <ul id="existingflows" class="nav">
            </ul>
            <button id="create-btn" class="btn btn-primary col-sm-12">Create Workflow</button>
            <div style="clear:both;"></div>
        </div>
        <div class="col-md-10">
            <form class="form-horizontal" role="form" id="workflow-form" name="workflow-form">
                <input type="hidden" id="workflow._id" name="workflow._id" value=""/>
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <div class="form-group">
                            <label for="workflow.name" class="col-sm-2 control-label">Workflow Name</label>
                            <div class="col-sm-10">
                                <h4 class="panel-title editable">
                                    <input type="text" class="form-control" name="workflow.name" id="workflow.name" value="">
                                </h4>
                            </div>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="form-group">
                            <label for="workflow.time_elapsed" class="col-sm-2 control-label">Time Elapsed</label>
                            <div class="col-sm-10">
                                <input type="number" class="form-control input-sm" name="workflow.time_elapsed" id="workflow.time_elapsed" value="">
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="prereqs" class="col-sm-2 control-label">Prerequisites</label>
                            <div class="col-sm-10">
                                <table class="table table table-condensed table-bordered">
                                    <thead>
                                        <tr>
                                            <th class="col-sm-1"><i class="glyphicon glyphicon-cog"></i></th>
                                            <th class="col-sm-6">Name</th>
                                            <th class="col-sm-5">Time Elapsed</th>
                                        </tr>
                                    </thead>
                                    <tbody id="prereqsList">
                                        <tr id="addPrereq-link">
                                            <td colspan="3">
                                                <a id="add-prereq-btn" href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="Add Prerequisite">
                                                    <i class="glyphicon glyphicon-plus"></i>
                                                </a>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.query_string" class="col-sm-2 control-label">Query String</label>
                            <div class="col-sm-10">
                                <textarea id="workflow.query_string" name="workflow.query_string" class="form-control input-sm" rows="10"></textarea>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="name" class="col-sm-2 control-label">Actions</label>
                            <div class="col-sm-10">
                                <table class="table table table-condensed table-bordered">
                                    <thead>
                                        <tr>
                                            <th class="col-sm-3">Name</th>
                                            <th class="col-sm-9">Args</th>
                                        </tr>
                                    </thead>
                                    <tbody id="actionsList">
                                        <tr id="addAction-link">
                                            <td colspan="2">
                                                <a id="add-action-btn" href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="Add Action">
                                                    <i class="glyphicon glyphicon-plus"></i>
                                                </a>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="btn-group pull-right">
                        <button id="test-workflow-link" type="button" class="btn btn-warning ladda-button" data-style="slide-left"><span class="ladda-label">Test Workflow&nbsp;<i class="glyphicon glyphicon-cog"></i></span></button>
                        <button id="save-link" type="button" class="btn btn-primary ladda-button" data-style="slide-left"><span class="ladda-label">Save Workflow&nbsp;<i class="glyphicon glyphicon-cloud-upload"></i></span></button>
                        <button type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown">
                            <span class="caret"></span>
                            <span class="sr-only">Toggle Dropdown</span>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-right" role="menu">
                            <li><a id="save-copy-link" href="javascript:void(0);">Save as New Workflow</a></li>
                        </ul>
                    </div>
                </div>
            </form>
        </div>
    </div>
    <div class="row" style="height:40px;"><div class="col-sm-12"></div></div>
    <div class="row">
        <div id="test-workflow-form" class="col-lg-10 col-md-10 col-lg-offset-2 col-md-offset-2" style="display:none">
            <div class="panel-group" id="accordion">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">
                            <span>Test Results</span>
                            <div class="pull-right">
                                <button id="test-workflow-close" type="button" class="close"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>
                            </div>
                        </h4>
                        <div style="clear:both"></div>
                    </div>
                    <div class="panel-body">
                        <h4>Test Summary</h4>
                        <div id="test-workflow-summary"></div>
                        <h4>Matching Tickets</h4>
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>Ticket</th>
                                    <th>Workflows Performed</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody id="test-workflow-results">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
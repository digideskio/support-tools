<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Support Issue Workflows</h1>
        </div>
    </div>
    <div class="row">
        <div class="col-lg-2 sidebar well" id="sidebar" role="navigation">
            <h4>Existing Workflows</h4>
            <ul id="existingflows" class="nav">
            </ul>
            <button id="create-btn" class="btn btn-primary col-sm-12">Create New Workflow</button>
            <div style="clear:both;"></div>
        </div>
        <div class="col-lg-10">
            <form class="form-horizontal" role="form" id="form">
                <input type="hidden" id="workflow._id" name="workflow._id" value=""/>
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <div class="form-group">
                            <label for="name" class="col-sm-2 control-label">Workflow Name</label>
                            <div class="col-sm-10">
                                <h4 class="panel-title editable">
                                    <input type="text" class="form-control" name="workflow.name" id="workflow.name" value="">
                                </h4>
                            </div>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="form-group">
                            <label for="name" class="col-sm-2 control-label">Time Elapsed</label>
                            <div class="col-sm-10">
                                <input type="number" class="form-control" name="workflow.time_elapsed" id="workflow.time_elapsed" value="">
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="prereqs" class="col-sm-2 control-label">Prerequisites</label>
                            <div class="col-sm-10">
                                <table class="table table table-condensed table-bordered">
                                    <thead>
                                        <tr>
                                            <th class="col-sm-6">Name</th>
                                            <th class="col-sm-6">Time Elapsed</th>
                                        </tr>
                                    </thead>
                                    <tbody id="prereqsList" name="prereqsList">
                                        <tr id="addPrereq-link">
                                            <td colspan="2">
                                                <a id="add-prereq-btn" href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="Add Prerequisite"><i class="glyphicon glyphicon-plus"></i></a>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="name" class="col-sm-2 control-label">Query String</label>
                            <div class="col-sm-10">
                                <textarea id="workflow.query_string" name="workflow.query_string" class="form-control" rows="10"></textarea>
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
                                    <tbody id="actionsList" name="actionsList">
                                        <tr id="addAction-link">
                                            <td colspan="2">
                                                <a id="add-action-btn" href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="Add Action"><i class="glyphicon glyphicon-plus"></i></a>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="btn-group pull-right">
                        <button id="save-link" type="button" class="btn btn-primary">Save Workflow&nbsp;<i class="glyphicon glyphicon-cloud-upload"></i></button>
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
</div>
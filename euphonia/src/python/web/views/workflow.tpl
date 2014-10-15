% _id = workflow['_id']
<form class="form-horizontal" role="form" id="form{{windex}}">
    <input type="hidden" id="workflow[{{windex}}]._id" name="workflow[{{windex}}]._id" value="{{_id}}"/>
    <div class="panel panel-default">
        <div class="panel-heading">
            <div class="form-group">
                <label for="name" class="col-sm-2 control-label">Workflow Name</label>
                <div class="col-sm-10">
                    <h4 class="panel-title editable">
                        <input type="text" class="form-control" name="workflow[{{windex}}].name" id="workflow[{{windex}}].name" value="{{workflow['name']}}">
                    </h4>
                </div>
            </div>
        </div>
        <div class="panel-body">
            <div class="form-group">
                <label for="name" class="col-sm-2 control-label">Time Elapsed</label>
                <div class="col-sm-10">
                    <input type="number" class="form-control" name="workflow[{{windex}}].time_elapsed" id="workflow[{{windex}}].time_elapsed" value="{{int(workflow['time_elapsed'])}}">
                </div>
            </div>
            <div class="form-group">
                <label for="prereqs" class="col-sm-2 control-label">Prereqs</label>
                <div class="col-sm-10">
                    <select multiple="true" class="form-control" name="workflow[{{windex}}].prereqs[]" id="workflow[{{windex}}].prereqs[]">
                        % for wf in workflows:
                        %     wfname = wf['name']
                        %     selected = ""
                        %     if wfname in workflow['prereqs']:
                        %         selected = 'selected="True"'
                        %     end
                        %     if wfname != workflow['name']:
                              <option value="{{wfname}}" {{selected}}>{{wfname}}</option>
                        %     end
                        % end
                    </select>
                </div>
            </div>
            <div class="form-group">
                <label for="name" class="col-sm-2 control-label">Query String</label>
                <div class="col-sm-10">
                    <script>var jstring = JSON.stringify({{!workflow['query_string']}},null,4); document.write('<textarea name="workflow[{{windex}}].query_string" class="form-control" rows="10">' + jstring + '</textarea>');</script>
                </div>
            </div>
            <div class="form-group">
                <label for="name" class="col-sm-2 control-label">Action Name</label>
                <div class="col-sm-10">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th class="col-sm-3">Name</th>
                                <th class="col-sm-9">Args</th>
                            </tr>
                        </thead>
                        <tbody>
                        % if len(workflow['actions']) > 0:
                            % aindex = 0
                            % for action in workflow['actions']:
                            <tr>
                                <td class="col-sm-3">
                                    <input id="workflow[{{windex}}].actions[{{aindex}}].name" name="workflow[{{windex}}].actions[{{aindex}}].name" class="form-control" value="{{!action['name']}}"/>
                                    <br/>
                                    <a href="javascript:void(0);" onclick="removeAction($(this).closest('tr'))"><i class="glyphicon glyphicon-minus"></i>&nbsp;Remove Action</a>
                                </td>
                                <td class="col-sm-9">
                                % if 'args' in action and len(action['args']) > 0:
                                %     argindex = 0
                                %     for arg in action['args']:
                                        <div class="form-group">
                                            <div class="col-sm-11">
                                                <textarea id="workflow[{{windex}}].actions[{{aindex}}].args[{{argindex}}]" name="workflow[{{windex}}].actions[{{aindex}}].args[{{argindex}}]" class="form-control" rows="10">{{arg}}</textarea>
                                            </div>
                                            <div class="col-sm-1">
                                                <a href="javascript:void(0);" onclick="removeArgument($(this).parent().parent())"><i class="glyphicon glyphicon-minus"></i></a>
                                            </div>
                                        </div>
                                %     end
                                % else:
                                    <div class="form-group">
                                        <div class="col-sm-11">
                                            <textarea id="workflow[{{windex}}].actions[{{aindex}}].args[0]" name="workflow[{{windex}}].actions[{{aindex}}].args[0]" class="form-control" rows="10"></textarea>
                                        </div>
                                        <div class="col-sm-1">
                                            <a href="javascript:void(0);" onclick="removeArgument($(this).parent().parent())"><i class="glyphicon glyphicon-minus"></i></a>
                                        </div>
                                    </div>
                                % end
                                    <div class="pull-right">
                                        <a href="javascript:void(0);" onclick="cloneArgument($(this).parent('div').prev())" class="pull-right">Add Argument&nbsp;<i class="glyphicon glyphicon-plus"></i></a>
                                    </div>
                                </td>
                            % aindex = aindex + 1
                            </tr>
                            % end
                        % else:
                            <tr>
                                <td class="col-sm-3">
                                    <input id="workflow[{{windex}}].actions[0].name" name="workflow[{{windex}}].actions[0].name" class="form-control" value=""/>
                                </td>
                                <td class="col-sm-9">
                                    <div class="form-group">
                                        <div>
                                            <textarea id="workflow[{{windex}}].actions[0].args[0]" name="workflow[{{windex}}].actions[0].args[0]" class="form-control" rows="10"></textarea>
                                        </div>
                                    </div>
                                    <div class="pull-right">
                                        <a href="javascript:void(0);" onclick="cloneArgument($(this).parent('div').prev())" class="pull-right">Add Argument&nbsp;<i class="glyphicon glyphicon-plus"></i></a>
                                    </div>
                                </td>
                            </tr>
                        % end
                        <tr><td colspan="2"><a href="javascript:void(0);" onclick="cloneAction($(this).closest('tr').prev())"><i class="glyphicon glyphicon-plus"></i>&nbsp;Add New Action</a></td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</form>
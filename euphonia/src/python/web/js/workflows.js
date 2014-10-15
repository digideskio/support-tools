var workflowsObj = {};
var workflows = [];

$(document).ready(function() {
    getWorkflowList();
    $('.create-btn').click(function(){clearForm()});
    $('#add-action-btn').click(function(){addAction()})
        .tooltip()
        .hover(
            function(){$(this).closest('tr').addClass('bg-success')},
            function(){$(this).closest('tr').removeClass('bg-success')}
    );
});

function renderList(workflows) {
    for(var wf in workflows){
        var workflow = workflows[wf];
        var el = $('<li></li>');
        var item = $('<a href="javascript:void(0);" class="col-sm-10">' + workflow['name'] + '</a>');
        var removelink = $('<a href="javascript:void(0);" class="text-danger col-sm-2" data-toggle="tooltip" data-placement="top" title="Remove Workflow"><i class="glyphicon glyphicon-trash"></i></a>').tooltip();
        removelink.click(wf,function(e){removeWorkflow(e.data)});
        item.click(wf,function(e){renderWorkflow(e.data);});
        item.appendTo(el);
        removelink.appendTo(el);
        el.appendTo($('#existingflows'));
    }
}

function getWorkflowList(){
    $.ajax({
        type: "GET",
        url: "/workflow",
        datatype: "json"
    }).success(function(response){
        workflowsObj = JSON.parse(response);
        for(var wf in workflowsObj['workflows']){
            var wfObj = workflowsObj['workflows'][wf];
            var id = wfObj['_id']['$oid'];
            workflows[id] = wfObj;
        }
        renderList(workflows);
    });
}

function renderWorkflow(wfid) {
    clearForm();
    var workflow = workflows[wfid];
    $(":input[id='workflow.name']").val(workflow['name']);
    $(":input[id='workflow._id']").val(workflow['_id']['$oid']);
    $(":input[id='workflow.time_elapsed']").val(workflow['time_elapsed']);
    for (var wf in workflows) {
        $('<option></option>').text(workflows[wf]['name']).val(workflows[wf]['name']).appendTo($(":input[id='workflow.prereqs']"))
    }
    var prereqs = workflow['prereqs'];
    for (var prereq in prereqs) {
        console.log(prereqs[prereq]);
        $(":input[id='workflow.prereqs']").find("option[value ='" + prereqs[prereq] + "']").attr('selected','true');
    }
    var jstring = JSON.stringify(workflow['query_string'],null,4);
    $(":input[id='workflow.query_string']").val(workflow['query_string']);
    renderActions(workflow['actions']);
}

function removeWorkflow(wfid){
    clearForm();
    /*
    $.ajax({
        type: "DELETE",
        url: "/workflow",
        datatype: "json"
    }).success(function(response){
        workflowsObj = JSON.parse(response);
        for(var wf in workflowsObj['workflows']){
            var wfObj = workflowsObj['workflows'][wf];
            var id = wfObj['_id']['$oid'];
            workflows[id] = wfObj;
        }
        renderList(workflows);
    });
    */
    alert("Deleted " + wfid);
}

function clearForm(){
    $(':input').val("");
    $(":input[id='workflow.prereqs']").empty()
    $("#actionsList").empty()
}

function renderActions(actions) {
    var parent = $('#actionsList');
    for (var action in actions) {
        var root = renderAction(actions[action],action);
        root.appendTo(parent);
    }
    var addaction = renderAddAction();
    addaction.appendTo(parent);
}

function renderAction(action,index){
    var root = $('<tr id="action-' + index + '"></tr>');
    var namenode = renderActionName(action, index);
    var argsnode = renderActionArgs(action, index);
    namenode.appendTo(root);
    argsnode.appendTo(root);
    return root;
}

function renderActionName(action, index){
    var root = $('<td class="col-sm-3"></td>');
    var nameinput = $('<input id="workflow.actions[' + index +'].name" name="workflow.actions[' + index +'].name" class="form-control"/>');
    if(action && action['name']){
        nameinput.val(action['name']);
    }
    var removelink = $('<a href="javascript:void(0);" class="text-danger remove-row" data-toggle="tooltip" data-placement="top" title="Remove Action"><i class="glyphicon glyphicon-trash"></i></a>').tooltip().hover(function(){$(this).closest('tr').addClass('bg-danger')},function(){$(this).closest('tr').removeClass('bg-danger')});
    removelink.on('click',function(){removeAction($(this).closest('tr'));});
    nameinput.appendTo(root);
    $('<br/>').appendTo(root);
    removelink.appendTo(root);
    return root;
}

function renderActionArgs(action,index){
    var root = $('<td id="action-"' + index + '-args" class="col-sm-9">');
    if(action && action['args']) {
        for (arg in action['args']) {
            var arginput = actionArgHtml(index,arg);
            arginput.find('textarea').val(action['args'][arg]);
            arginput.appendTo(root);
        }
    }
    addarg = renderAddActionArg(index);
    addarg.appendTo(root);
    return root;
}

function actionArgHtml(actionindex,argindex){
    var content = '<div class="form-group"> \
                <div class="col-sm-11"> \
                    <textarea id="workflow.actions[' + actionindex + '].args[' + argindex + ']" name="workflow.actions[' + actionindex + '].args[' + argindex + ']" class="form-control" rows="10"></textarea> \
                </div> \
                <div class="col-sm-1"> \
                    <a href="javascript:void(0);" class="pull-right text-danger remove-argument-link" data-toggle="tooltip" data-placement="top" title="Remove Argument"><i class="glyphicon glyphicon-trash"></i></a> \
                </div> \
            </div>';
    var root = $(content)
    root.find('.remove-argument-link')
        .click(function(){removeActionArg($(this).parent().parent())})
        .tooltip()
        .hover(function(){$(this).closest('td').addClass('bg-danger')},function(){$(this).closest('td').removeClass('bg-danger')});
    return root;
}

function renderAddAction(){
    var root = $('<tr id="addAction-link"></tr>');
    var col = $('<td colspan="2"></td>');
    var link = $('<a href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="Add Action"><i class="glyphicon glyphicon-plus"></i></a>').tooltip().hover(function(){$(this).closest('tr').addClass('bg-success')},function(){$(this).closest('tr').removeClass('bg-success')});
    link.click(function(){addAction()});
    link.appendTo(col);
    col.appendTo(root);
    return root;
}

function renderAddActionArg(actionindex){
    var root = $('<div id="addActionArg-' + actionindex + '-link" class="pull-right"></div>');
    var link = $('<a href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="Add Argument"><i class="glyphicon glyphicon-plus"></i></a>').tooltip().hover(function(){$(this).closest('td').addClass('bg-success')},function(){$(this).closest('td').removeClass('bg-success')});
    link.click(function(){addActionArg(actionindex)});
    link.appendTo(root);
    return root;
}

function removeAction(parent){
    $(parent).remove();
}

function removeActionArg(parent) {
    $(parent).remove();
}

function addAction(){
    var link = $('#addAction-link');
    var container = link.parent();
    var argindex = container.children().length - 1;
    var content = renderAction(null,argindex);
    if(argindex == 0){
        container.prepend(content);
    } else {
        link.prev().after(content);
    }
}

function addActionArg(actionindex){
    var link = $('#addActionArg-' + actionindex + '-link');
    var container = link.parent();
    var argindex = container.children().length - 1;
    var content = actionArgHtml(actionindex,argindex);
    if(argindex == 0){
        container.prepend(content);
    } else {
        link.prev().after(content);
    }
}

function saveChanges(form) {
    var formid = $(form).attr('id');
    var jsonform = form2js(document.getElementById(formid),".",true,undefined,true,true);
    formdata = JSON.stringify(jsonform,null,4);
    /*
    $.ajax({
       type : "POST",
       url : "/editworkflow",
       data : formdata
    }).success(function(){
        getWorkflowList();
    });
    */
    alert("Saved workflow");
}

function saveChangesNew(form) {
    var formid = $(form).attr('id');
    var jsonform = form2js(document.getElementById(formid),".",true,undefined,true,true);
    formdata = JSON.stringify(jsonform,null,4);
    /*
    $.ajax({
       type : "POST",
       url : "/editworkflow",
       data : formdata
    }).success(function(){
        getWorkflowList();
    });
    */
    alert("Saved workflow as a new copy");
}
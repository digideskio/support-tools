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
    $('#add-prereq-btn').click(function(){addPrereq()})
        .tooltip()
        .hover(
            function(){$(this).closest('tr').addClass('bg-success')},
            function(){$(this).closest('tr').removeClass('bg-success')}
    );
    $('#save-link').click(function(){saveChanges($(this).closest('form'));})
    $('#save-copy-link').click(function(){saveChangesNew($(this).closest('form'));})
});

function renderList(workflows) {
    $('#existingflows').empty();
    for(var wf in workflows){
        var workflow = workflows[wf];
        var el = $('<li></li>');
        var item = $('<a href="javascript:void(0);" class="col-sm-10">' + workflow['name'] + '</a>');
        var removelink = $('<a href="javascript:void(0);" class="text-danger col-sm-1" data-toggle="tooltip" data-placement="top" title="Remove Workflow"><i class="glyphicon glyphicon-trash"></i></a>').tooltip();
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
    renderPrereqs(workflow['prereqs']);
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
    $("#prereqsList").empty();
    $("#actionsList").empty();
    renderActions();
    renderPrereqs();
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
    var root = $('<tr id="action-' + index + '" class="action"></tr>');
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

function renderPrereqs(prereqs) {
    var parent = $('#prereqsList');
    for (var prereq in prereqs) {
        var root = renderPrereq(prereqs,prereq);
        root.appendTo(parent);
    }
    var addprereq = renderAddPrereq();
    addprereq.appendTo(parent);
}


function renderPrereq(prereqs,index){
    var prereq = null;
    if(prereqs && prereqs[index]){
        prereq = prereqs[index];
    }
    var root = $('<tr id="prereq-' + index + '" class="prereq"></tr>');
    var col1 = $('<td class="col-sm-6"></td>');
    var col2 = $('<td class="col-sm-6"></td>');
    var content1 = $('<select id="workflow.prereqs[' + index +'].name" name="workflow.prereqs[' + index +'].name" class="form-control"></select');
    var content2 = $('<input id="workflow.prereqs[' + index +'].time_elapsed" name="workflow.prereqs[' + index +'].time_elapsed" class="form-control"/>');
    $('<option></option>').val("").appendTo(content1);
    for (var wf in workflows) {
        $('<option></option>').text(workflows[wf]['name']).val(workflows[wf]['name']).appendTo(content1);
    }
    if(prereq && prereq['name']){
        content1.val(prereq['name']);
    }
    if(prereq && prereq['time_elapsed']){
        content2.val(prereq['time_elapsed']);
    }
    content1.appendTo(col1);
    content2.appendTo(col2);
    col1.appendTo(root);
    col2.appendTo(root);
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

function renderAddPrereq(){
    var root = $('<tr id="addPrereq-link"></tr>');
    var col = $('<td colspan="2"></td>');
    var link = $('<a href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="Add Prerequisite"><i class="glyphicon glyphicon-plus"></i></a>').tooltip().hover(function(){$(this).closest('tr').addClass('bg-success')},function(){$(this).closest('tr').removeClass('bg-success')});
    link.click(function(){addPrereq()});
    link.appendTo(col);
    col.appendTo(root);
    return root;
}

function removeAction(parent){
    $(parent).remove();
}

function removeActionArg(parent) {
    $(parent).remove();
}

function removePrereq(parent){
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

function addPrereq(){
    var link = $('#addPrereq-link');
    var container = link.parent();
    var argindex = container.children().length - 1;
    var content = renderPrereq(null);
    if(argindex == 0){
        container.prepend(content);
    } else {
        link.prev().after(content);
    }
}

function saveChanges(form) {
    var formid = $(form).attr('id');
    var jsonform = form2js(document.getElementById(formid),".",true,undefined,true,true);
    var formdata = JSON.stringify(jsonform,null,4);
    var url = "/workflow/" + jsonform.workflow.name;
    saveWorkflow(formdata,url);
}

function saveChangesNew(form) {
    var formid = $(form).attr('id');
    var jsonform = form2js(document.getElementById(formid),".",true,undefined,true,true);
    delete jsonform.workflow._id;
    var formdata = JSON.stringify(jsonform,null,4);
    var url = "/workflow"
    saveWorkflow(formdata,url);
}

function saveWorkflow(content,url){
    $.ajax({
        type : "POST",
        url : url,
        data : content
    }).success(function(){
        getWorkflowList();
        alert("Saved workflow");
        clearForm();
    }).error(function(e){
        alert("Workflow was NOT saved for the following reason:\n" + e.status + " : " + e.statusText );
        console.log(e);
    });
}
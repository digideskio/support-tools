$(document).ready(function() {
    $('.form-control').blur(function(){saveChanges($(this).closest("form"))});
 });

function saveChanges(form) {
    var formid = $(form).attr('id');
    var jsonform = form2js(document.getElementById(formid),".",true,undefined,true,true);
    formdata = JSON.stringify(jsonform,null,4);
    $.ajax({
       type : "POST",
       url : "/editworkflow",
       data : formdata
    });
}

function cloneArgument(original) {
    var newnode = $(original).clone();
    var input = newnode.find('.form-control');
    var argCount = $(original).parent().find("div").size() - 1;
    var newid = input.attr('id').replace(/\.args\[\d+\]/,".args[" + argCount + "]");
    input.attr('id',newid);
    input.attr('name',newid);
    input.val();
    input.text("");
    newnode.find('.form-control').blur(function(){saveChanges($(this).closest("form"))});
    original.after(newnode);
}

function removeArgument(node) {
    $(node).remove();
}

function cloneAction(original) {
    var newnode = $(original).clone();
    var input = newnode.find('td input');
    var actionCount = $(original).closest("tbody").find("tr").size() - 1;
    var newid = input.attr('id').replace(/\.actions\[\d+\]\.name/,".actions[" + actionCount + "].name")
    input.attr('id',newid);
    input.attr('name',newid);
    newnode.find(':input').each(function(){
        $(this).attr('id').replace(/\.actions\[\d+\]\./,".actions[" + actionCount + "].");
        $(this).val('');
    });
    newnode.find('.form-control').blur(function(){saveChanges($(this).closest("form"))});
    original.after(newnode);
}

function removeAction(node) {
    $(node).remove();
}
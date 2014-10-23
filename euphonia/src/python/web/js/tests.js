var testsObj = {};
var tests = [];
var defined_tests = {};

$(document).ready(function() {
    getTestList();
    getDefinedTestList();
    $('#create-btn').click(function(){clearForm()});
    $('#save-link').click(function(){saveChanges($(this).closest('form'));});
    $('#save-copy-link').click(function(){saveChangesNew($(this).closest('form'));});
    $('#test-link').click(function(){testTest();});
    $('#test-close').click(function(){$('#test-form').hide();});
});

function renderList(tests) {
    var list = $('#existingtests');
    list.empty();
    for(var t = 0; t < tests.length; t++){
        var test = tests[t];
        var el = $('<li></li>');
        var item = $('<a href="javascript:void(0);" class="col-xs-9">' + test['name'] + '</a>');
        var removelink = $('<a href="javascript:void(0);" class="text-danger col-xs-1"><i class="glyphicon glyphicon-trash" data-toggle="tooltip" data-placement="top" title="Remove Test"></i></a>');
        removelink.find('i').tooltip();
        removelink.click(test.name,function(e){removeTest(e.data)});
        item.click(t,function(e){renderTest(e.data);});
        item.appendTo(el);
        removelink.appendTo(el);
        el.appendTo(list);
    }
}

function getTestList(){
    $.ajax({
        type: "GET",
        url: "/test",
        datatype: "json"
    }).success(function(response){
        tests = [];
        var responseObj = JSON.parse(response);
        if (responseObj.status == "success") {
            testsObj = responseObj.data;
            for (var t = 0; t < testsObj['tests'].length; t++) {
                var tObj;
                tObj = testsObj['tests'][t];
                tests[t] = tObj;
            }
            renderList(tests);
        } else {
            alert("Could not load test list.");
        }
    });
}

function getDefinedTestList(){
    $.ajax({
        type: "GET",
        url: "/defined_tests",
        datatype: "json"
    }).success(function(response){
        defined_tests = [];
        var responseObj = JSON.parse(response);
        if (responseObj.status == "success") {
            var defined_testsObj = responseObj;
            if(defined_testsObj['data']['defined_tests'] != undefined){
                defined_tests = defined_testsObj['data']['defined_tests'];
            }
        } else {
            alert("Could not load defined test list.");
        }
    });
}

function renderTest(tid) {
    clearForm();
    var test = tests[tid];
    console.log(tid);
    var tname = test['name'];
    var testobj = defined_tests[tname];
    console.log(testobj);
    showTestExistsAlert(testobj);
    $(":input[id='test.name']").val(test['name']);
    $(":input[id='test._id']").val(test['_id']['$oid']);
    $(":input[id='test.active']").prop('checked',test['active']);
    $(":input[id='test.priority']").val(test['priority']);
    $(":input[id='test.comment']").val(test['comment']);
}

function showTestExistsAlert(test){
    var container = $('#test-exists');
    if(test != undefined){
        container.addClass("alert-success");
        container.removeClass("alert-danger");
        container.html('This test is defined and available for use:<br/><pre class="prettyprint">' + test + '</pre>');
    } else {
        container.addClass("alert-danger");
        container.removeClass("alert-success");
        container.html("This test is NOT defined and cannot be used.")
    }
    prettyPrint();
    container.show();
}

function removeTest(tname){
    if(confirm("Are you sure you want to delete test " + tname + "?")){
        clearForm();
        $.ajax({
            type: "DELETE",
            url: "/test/" + tname,
            datatype: "json"
        }).success(function(){
            console.log("Deleted " + tname);
            getTestList();
        });
    } else {
        return false;
    }
}

function clearForm(){
    $(':input').val("");
    $(':checkbox').prop('checked',false);
    $("#test-result-form").hide();
    $("#test-exists").hide();
}

function saveChanges(form) {
    var formid = $(form).attr('id');
    var jsonform = form2js(document.getElementById(formid), ".", true, undefined, true, true);
    jsonform['test']['active'] = $(":input[id='test.active']").prop('checked');
    var formdata = JSON.stringify(jsonform, null, 4);
    var url = "/test/" + jsonform['test']['name'];
    var exists = false;
    for (var t = 0; t < tests.length; t++) {
        if (tests[t]['name'] == jsonform['test']['name'] && tests[t]['_id']['$oid'] != jsonform['test']['_id']) {
            exists = true;
        }
    }
    if (exists) {
        alert("A test named " + jsonform['test']['name']+ " already exists. Changes have not been saved.");
        return false;
    } else {
        saveTest(formdata, url);
    }
}

function saveChangesNew(form) {
    var formid = $(form).attr('id');
    var jsonform = form2js(document.getElementById(formid), ".", true, undefined, true, true);
    delete jsonform['test']['_id'];
    jsonform['test']['active'] = $(":input[id='test.active']").prop('checked');
    var formdata = JSON.stringify(jsonform, null, 4);
    var url = "/test";
    var exists = false;
    for (var t = 0; t < tests.length; t++) {
        if (tests[t]['name'] == jsonform['test']['name']) {
            exists = true;
        }
    }
    if (exists) {
        alert("A test named " + jsonform['test']['name'] + " already exists. Changes have not been saved.");
        return false;
    } else {
        saveTest(formdata, url);
    }
}

function saveTest(content,url){
    var lsave = Ladda.create(document.querySelector('#save-link'));
	lsave.start();
    $.ajax({
        type : "POST",
        url : url,
        data : content
    }).success(function(){
        getTestList();
        clearForm();
    }).error(function(e){
        alert("Test was NOT saved for the following reason:\n" + e.status + " : " + e.statusText );
        console.log(e);
    }).always(function(){
        lsave.stop();
    });
}

function testTest(){
    var groups = $('#test-results');
    groups.empty();
    var jsonform = form2js(document.getElementById('test-form'),".",true,undefined,true,true);
    var url = "/test/" + jsonform['test']['name'];
    var l = Ladda.create(document.querySelector('#test-link'));
	l.start();
    $.ajax({
        type : "GET",
        url : url,
        datatype : "json",
        async: true
    }).success(function(response){
        var responseObj = JSON.parse(response);
        if(responseObj.status == "success") {
            renderGroups(responseObj.data, groups);
        }
        $('#test-result-form').show();
    }).error(function(e){
        console.log(e);
        return false;
    }).always(function(){
        l.stop();
    });
}

function renderGroups(groups,container){
    if(groups['groups'] != undefined) {
        groups = groups['groups'];
        for (var i = 0; i < groups.length; i++) {
            var group = groups[i];
            $('<tr>' +
            '<td>' +
            '<a target="_blank" href="/group/' + group['GroupId'] + '">' + group['GroupName'] + '</a>' +
            '</td>' +
            '<td>' + '' + '</td>' +
            '<td>' + '' + '</td>' +
            '</tr>').appendTo(container);
        }
    }
}
var testsObj = {};
var tests = [];
var defined_tests = {};

function getTestList(){
    "use strict";
    $.ajax({
        type: "GET",
        url: "/test",
        datatype: "json"
    }).success(function(response){
        tests = [];
        var responseObj = JSON.parse(response);
        if (responseObj.status === "success") {
            testsObj = responseObj.data;
            for (var t = 0; t < testsObj.tests.length; t++) {
                var tObj;
                tObj = testsObj.tests[t];
                tests[tObj.name] = tObj;
            }
            renderList(tests);
        } else {
            alert("Could not load test list.");
        }
    });
}

function getDefinedTestList(){
    "use strict";
    $.ajax({
        type: "GET",
        url: "/defined_tests",
        datatype: "json"
    }).success(function(response){
        defined_tests = [];
        var responseObj = JSON.parse(response);
        if (responseObj.status === "success") {
            var defined_testsObj = responseObj;
            if(defined_testsObj.data.defined_tests !== undefined){
                defined_tests = defined_testsObj.data.defined_tests;
            }
        } else {
            alert("Could not load defined test list.");
        }
    });
}

function renderTest(tid) {
    clearForm();
    var test = tests[tid];
    var tname = test.name;
    var testobj = defined_tests[tname];
    showTestExistsAlert(testobj);
    $(":input[id='test.name']").val(test.name);
    $(":input[id='test._id']").val(test._id.$oid);
    $(":input[id='test.active']").prop('checked',test.active);
    $(":input[id='test.priority']").val(test.priority);
    $(":input[id='test.comment']").val(test.comment);
    $(this).addClass("active");
}

function renderClick() {
    return function(e){ renderTest(e.data); };
}

function renderRemoveClick() {
    return function(e){ removeTest(e.data); };
}

function renderList(tests) {
    "use strict";
    var list = $('#existingtests');
    list.empty();
    var collections = {};
    for (var t in tests){
        var tt = tests[t];
        var collname = tt.collection;
        if(collname === undefined){
            if(collections['No Collection'] === undefined) {
                collections['No Collection'] = [];
            }
            collections['No Collection'].push(tt);
        } else {
            if(collections[collname] === undefined) {
                collections[collname] = [];
            }
            collections[collname].push(tt);
        }
    }
    console.log(collections);
    for (var coll in collections) {
        var colltests = collections[coll];
        //var colldivider = $('<li class="nav-divider"></li>');
        var colltitle = $('<li><span><i class="glyphicon glyphicon-folder-open"></i>' + "&nbsp; " + coll + '</span></li>');
        //colldivider.appendTo(list);
        colltitle.appendTo(list);
        for (var ct = 0; ct < colltests.length; ct++) {
            var test = colltests[ct];
            var el = $('<li class="nav"></li>');
            var item = $('<a href="javascript:void(0);" class="col-xs-9">' + test.name + '</a>');
            var removelink = $('<a href="javascript:void(0);" class="text-danger col-xs-1"><i class="glyphicon glyphicon-trash" data-toggle="tooltip" data-placement="top" title="Remove Test"></i></a>');
            removelink.find('i').tooltip();
            removelink.click(test.name, renderRemoveClick());
            item.click(test.name, renderClick());
            item.appendTo(el);
            removelink.appendTo(el);
            el.appendTo(list);
        }
    }
}

function showTestExistsAlert(test){
    var container = $('#test-exists');
    if(test !== undefined){
        container.addClass("alert-success");
        container.removeClass("alert-danger");
        container.html('This test is defined and available for use:<br/><pre class="prettyprint">' + test + '</pre>');
    } else {
        container.addClass("alert-danger");
        container.removeClass("alert-success");
        container.html("This test is NOT defined and cannot be used.");
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
    jsonform.test.active = $(":input[id='test.active']").prop('checked');
    var formdata = JSON.stringify(jsonform, null, 4);
    var url = "/test";
    var exists = false;
    for (var t = 0; t < tests.length; t++) {
        if (tests[t].name === jsonform.test.name && tests[t]._id.$oid != jsonform.test._id) {
            exists = true;
        } else if (tests[t].name === jsonform.test.name) {
            url = "/test/" + jsonform.test.name;
        }
    }
    if (exists) {
        alert("A test named " + jsonform.test.name + " already exists. Changes have not been saved.");
        return false;
    } else {
        saveTest(formdata, url);
    }
}

function saveChangesNew(form) {
    var formid = $(form).attr('id');
    var jsonform = form2js(document.getElementById(formid), ".", true, undefined, true, true);
    delete jsonform.test._id;
    jsonform.test.active = $(":input[id='test.active']").prop('checked');
    var formdata = JSON.stringify(jsonform, null, 4);
    var url = "/test";
    var exists = false;
    for (var t = 0; t < tests.length; t++) {
        if (tests[t].name === jsonform.test.name) {
            exists = true;
        }
    }
    if (exists) {
        alert("A test named " + jsonform.test.name + " already exists. Changes have not been saved.");
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
    var url = "/test/" + jsonform.test.name;
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
    "use strict";
    if(groups.groups !== undefined) {
        groups = groups.groups;
        for (var i = 0; i < groups.length; i++) {
            var group = groups[i];
            $('<tr>' +
            '<td>' +
            '<a target="_blank" href="/group/' + group.GroupId + '">' + group.GroupName + '</a>' +
            '</td>' +
            '<td>' + group.priority + '</td>' +
            '<td>' + replaceStartDate(group.LastPageView.$date) + '</td>' +
            '<td>' + replaceStartDate(group.LastActiveAgentTime.$date) + '</td>' +
            '</tr>').appendTo(container);
        }
    }
}

function replaceStartDate(timestamp){
    var dateObj = new Date(timestamp);
    var year = dateObj.getUTCFullYear();
    var month = dateObj.getUTCMonth() + 1;
    if(month < 10){month = "0" + month;}
    var date = dateObj.getUTCDate();
    if(date < 10){date = "0" + date;}
    var hours = dateObj.getUTCHours();
    if(hours < 10){hours = "0" + hours;}
    var minutes = dateObj.getUTCMinutes();
    if(minutes < 10){minutes = "0" + minutes;}
    return year + "-" + month + "-" + date + " " + hours + ":" + minutes;
}

$(document).ready(function() {
    getTestList();
    getDefinedTestList();
    $('#create-btn').click(function () { clearForm(); });
    $('#save-link').click(function () { saveChanges($(this).closest('form')); });
    $('#save-copy-link').click(function () { saveChangesNew($(this).closest('form')); });
    $('#test-link').click(function () { testTest(); });
    $('#test-close').click(function () { $('#test-result-form').hide(); });
});
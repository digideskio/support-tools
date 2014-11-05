/**
 * @fileoverview This file contains the methods used by ../views/tests.tpl
 */

var testsObj = {};
var tests = [];
var defined_tests = {};

/**
 * Retrieves the set of tests from the database (via REST API).
 * @return {null}
 */
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

/**
 * Retrieves the set of tests defined in the code (via REST API)
 * @return {null}
 */
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

/**
 * Populates the form with a given test definition.
 * @param {string} tid Test ID
 * @return {null}
 */
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

/**
 * Generates an onclick function to render a test.
 * @return {function} function to be executed onclick
 */
function renderClick() {
    return function(e){ renderTest(e.data); };
}

/**
 * Generates an onclick function to remove a test.
 * @return {function} function to be executed onclick
 */
function renderRemoveClick() {
    return function(e){ removeTest(e.data); };
}

/**
 * Renders the sidenav list of existing tests.
 * @param {object} tests the list of tests to be rendered in the list
 * @return {null}
 */
function renderList(tests) {
    "use strict";
    var list = $('#existingtests');
    list.empty();
    // Retrieve set of test collections by iterating over the tests
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

    // Loop over collections, rendering each test in the collection
    for (var coll in collections) {
        var colltests = collections[coll];
        var colltitle = $('<li><span><i class="glyphicon glyphicon-folder-open"></i>' + "&nbsp; " + coll + '</span></li>');
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

/**
 * Renders a details box that shows if the test has been defined in Python code.
 * @param {object} test the test currently being rendered
 * @return {null}
 */
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

/**
 * Removes a given test via the REST API.
 * @param {string} tname the name of the test
 * @return {boolean}
 */
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
        return true;
    } else {
        return false;
    }
}

/**
 * Clears all the inputs on the tests form.
 * @return {null}
 */
function clearForm(){
    $(':input').val("");
    $(':checkbox').prop('checked',false);
    $("#test-result-form").hide();
    $("#test-exists").hide();
}

/**
 * Save a test definition to the database
 * @param {object} form the form object from the page
 * @return {boolean}
 */
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
        return true;
    }
}

/**
 * Save a test definition as a new item to the database
 * @param {object} form the form object from the page
 * @return {boolean}
 */
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
        return true;
    }
}

/**
 * Saves a given test via the REST API.
 * @param {object} content the test definition document
 * @param {string} url the REST API URL to call
 * @return {function} function to be executed onclick
 */
function saveTest(content,url){
    // Display loading gif
    var lsave = Ladda.create(document.querySelector('#save-link'));
	lsave.start();
    $.ajax({
        type : "POST",
        url : url,
        data : content
    }).success(function(){
        // Repopulate list and clear the form
        getTestList();
        clearForm();
    }).error(function(e){
        alert("Test was NOT saved for the following reason:\n" + e.status + " : " + e.statusText );
        console.log(e);
    }).always(function(){
        lsave.stop();
    });
}

/**
 * Search the list of groups that have failed this particular
 * test (via the REST API).
 * @return {boolean} whether the call was successfully made
 */
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
        return true;
    }).error(function(e){
        console.log(e);
        return false;
    }).always(function(){
        l.stop();
    });
}

/**
 * Render the given list of groups that have failed a particular test.
 * @param {object} groups the list of group documents
 * @param {object} container the parent element where the list is rendered.
 * @return {null}
 */
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

/**
 * Formats a timestamp as a string for display
 * @param {int} timestamp to be rendered
 * @return {string} the formatted dateTime string
 */
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

/**
 * Executes logic when the page has completed loading.
 */
$(document).ready(function() {
    // Render existing tests
    getTestList();
    // Pre-populate set of tests defined in Python code
    getDefinedTestList();
    // Set onclick actions for form buttons
    $('#create-btn').click(function () { clearForm(); });
    $('#save-link').click(function () { saveChanges($(this).closest('form')); });
    $('#save-copy-link').click(function () { saveChangesNew($(this).closest('form')); });
    $('#test-link').click(function () { testTest(); });
    $('#test-close').click(function () { $('#test-result-form').hide(); });
});
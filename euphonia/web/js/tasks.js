/**
 * @fileoverview This file contains the methods used by ../views/tasks.tpl
 */

/**
 * Opens/Renders the Jira view of a given ticket.
 * @param {string} context the particular issue being selected/rendered
 * @param {string} url the Jira URL for the ticket
 * @param {string} issue the Jira ID of the ticket
 * @return {null}
 */
function showPage(context, url, issue) {
    var list = $('#ticketList');
    var frame = $('#ticketFrame');
    var content = $('#ticketContent');

    // Clear any actively selected items
    list.find('tr').each(function(){$(this).removeClass('info');});
    // Mark context as active
    $(context).closest('tr').addClass('info');

    // Setup/Render the preview pane
    frame.attr('src','');
    frame.attr('src',url);
    $('#ticketLink').attr('href',url);
    list.addClass('col-lg-6');
    list.removeClass('col-lg-12');
    $('#ticketTitle').find('span').text('Jira view of ' + issue);
    content.addClass('col-lg-6');
    content.height(Math.max(list.height(),600));
    content.show();
}

/**
 * Closes the Jira preview pane of a given ticket.
 * @return {null}
 */
function closePage() {
    var list = $('#ticketList');
    list.find('tr').each(function(){$(this).removeClass('info');});
    list.addClass('col-lg-12');
    list.removeClass('col-lg-6');
    $('#ticketContent').hide();
}

/**
 * Executes the action for a failure event.
 * @param {string} content to be displayed
 * @return {null}
 */
function failure(content){
    alert("unable to complete request: " + content);
}

/**
 * Applies changes to tasks via REST API
 * @param {string} task to act upon
 * @param {string} action to be taken
 * @param {function} success function to be executed on success
 * @param {function} failure function to be executed on failure
 * @param {int} seconds to sleep if a sleep action is executed
 * @return {null}
 */
function taskAction(task,action,success,failure,seconds) {
    var getURL = "/task/" + task + "/" + action;
    seconds = seconds || 0;
    if(seconds && seconds > 0) {
        getURL = getURL + "/" + seconds;
    }
    $.ajax({
        type: "GET",
        datatype: "json",
        url: getURL
    }).success(success).error(failure);
}

function tasksAction(tasks, action, args) {
    // TODO change this to a bulk call
    for (var i = 0; i < tasks.length; i++){
        task = tasks[i];
        if (typeof args !== "undefined") {
            action(task, args);
        } else {
            action(task);
        }
    }
}

function toggleSelect(el) {
    if (el.checked) {
        selectAll(el);
    } else {
        selectNone(el);
    }
}

function selectAll(el) {
    var form = $(el).closest("form")
    $("input[type=checkbox]", form).each(function(i, el){
        // unless they're inactive
        if ($(el).hasClass("inactive")) {
            return;
        }
        el.checked = true;
    });
}

function selectNone(el) {
    var form = $(el).closest("form")
    $("input[type=checkbox]", form).each(function(i, el){
        el.checked = false;
    });
}

function getCheckedTaskIdsFromNearestForm(el) {
    var form = $(el).closest("form")
    var taskIds = []
    $("input[type=checkbox]:checked", form).each(function(i, el){
        if ($(el).hasClass("inactive")) {
            return;
        }
        taskIds.push(el.value)
    });
    return taskIds;
}

/**
 * Remove a task from the list
 * @param {string} task to act upon
 * @return {null}
 */
var removeTask = function(task) {
    var success = function(){
        $('#' + task).remove();
    };
    taskAction(task,"remove",success,failure,0);
}

function removeTasks(el) {
    var tasks = getCheckedTaskIdsFromNearestForm(el);
    tasksAction(tasks, removeTask);
}

/**
 * Sleep a task in the list
 * @param {string} task to act upon
 * @param {int} seconds to sleep the task
 * @return {null}
 */
var sleepTask = function(task,seconds) {
    seconds = seconds || 0;
    var success = function(response){
        var json = JSON.parse(response);
        var taskObj = $('#' + task);
        taskObj.find('.stats').hide();
        if(seconds === 0){
            taskObj.addClass('frozen');
            $('#' + task + '-frozen').show();
            var workflow = json.data.task.workflow;
            if (isWorkflowInCookie(workflow, 'workflows_hide_frozen')) {
                $(taskObj).hide();
            }
        }
        replaceStartDate(task,json.data.task.start.$date);
    };
    taskAction(task,"sleep",success,failure,seconds);
}

function sleepTasks(el, seconds) {
    var tasks = getCheckedTaskIdsFromNearestForm(el);
    tasksAction(tasks, sleepTask, seconds);
}

/**
 * Wake a task on the list
 * @param {string} task to act upon
 * @return {null}
 */

var wakeTask = function(task) {
    var success = function(response){
        $('#' + task).removeClass('frozen');
        $('#' + task + '-frozen').hide();
        replaceStartDate(task,JSON.parse(response).data.task.start.$date);
    };
    taskAction(task,"wake",success,failure,0);
}

function wakeTasks(el) {
    var tasks = getCheckedTaskIdsFromNearestForm(el);
    tasksAction(tasks, wakeTask);
}

/**
 * Approve a task on the list
 * @param {string} task to act upon
 * @return {null}
 */

var approveTask = function(task) {
    var success = function(){
        var taskObj = $('#' + task);
        taskObj.find('.approve').toggle();
        taskObj.find('.stats').hide();
        $('#' + task + '-approve').show();
    };
    taskAction(task,"approve",success,failure,0);
}

function approveTasks(el) {
    var tasks = getCheckedTaskIdsFromNearestForm(el);
    tasksAction(tasks, approveTask);
}


/**
 * Disapprove a task on the list
 * @param {string} task to act upon
 * @return {null}
 */
var disapproveTask = function(task) {
    var success = function(){
        var taskObj = $('#' + task);
        taskObj.find('.approve').toggle();
        taskObj.find('.stats').hide();
    };
    taskAction(task,"disapprove",success,failure,0);
}

function disapproveTasks(el) {
    var tasks = getCheckedTaskIdsFromNearestForm(el);
    tasksAction(tasks, disapproveTask);
}

/**
 * Formats a timestamp as a string for display
 * @param {string} task to act upon
 * @param {int} timestamp to be rendered
 * @return {string} the formatted dateTime string
 */
function replaceStartDate(task,timestamp){
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
    var dateString = year + "-" + month + "-" + date + " " + hours + ":" + minutes;
    $('#' + task).find('.startdate').text(dateString);
}

/**
 * Executes logic when the page has completed loading.
 */
$(document).ready(function() {
    // Set a 60 second page refresh
    //window.setTimeout(function(){window.location.href = window.location.href;},60000);
    var hoverIn = function(evt) {
        $('.td_task_actions div', evt.currentTarget).css("display", "");
    }

    var hoverOut = function(evt) {
        $('.td_task_actions div', evt.currentTarget).css("display", "none");
    }

    $('.tr_task').hover(hoverIn, hoverOut);

    $('#selectWorkflowsDropdown').on('hidden.bs.dropdown', function() {
        $("#i_dropdown").removeClass("glyphicon-minus-sign");
        $("#i_dropdown").addClass("glyphicon-plus-sign");
    });

    $('#selectWorkflowsDropdown').on('shown.bs.dropdown', function() {
        $("#i_dropdown").removeClass("glyphicon-plus-sign");
        $("#i_dropdown").addClass("glyphicon-minus-sign");
    });

    // keep the dropdown open after items are checked or unchecked
    $('#selectWorkflowsDropdown .dropdown-menu').on({
        "click":function(e){
            e.stopPropagation();
        }
    });

    String.prototype.decodeOctalEscapeSequence = function() {
        return this.replace(/\\([0-7]{3})/g, function() {
            return String.fromCharCode(parseInt(arguments[1], 8));
        });
    };

    // initialize checkboxes
    var workflows = $.cookie('workflows');
    if (workflows) {
        // SimpleCookie bug imo introduced in http://bugs.python.org/issue9824
        workflows = workflows.decodeOctalEscapeSequence();
        workflows = JSON.parse(workflows);
        for (var i = 0; i < workflows.length; i++){
            var checkbox = "#checkbox_"+workflows[i];
            $(checkbox).attr("checked", true)
        }
    }

    $('.selectWorkflowsDropdownCheckbox').click(function(evt){
        var checked = evt.currentTarget.checked;
        var uid = $.cookie('_id')
        var value = evt.currentTarget.value;

        // update cookie
        var workflows = $.cookie('workflows');
        // SimpleCookie bug imo introduced in http://bugs.python.org/issue9824
        workflows = workflows.decodeOctalEscapeSequence();
        workflows = JSON.parse(workflows)
        if (checked) {
            // persist server-side
            $.post('/user/'+uid+'/workflow/'+value, function(res) {
                //console.log(res)
            });
            // persist client-side
            workflows.push(value);
            addWorkflow(value);
        } else {
            // persist server-side
            $.ajax({
                url: '/user/'+uid+'/workflow/'+value,
                type: 'DELETE',
                success: function(res) {
                    //console.log(res)
                }
            });
            // persist client-side
            for (var i = 0; i < workflows.length; i++){
                if (workflows[i] === value) {
                    var tmp = workflows.splice(0, i);
                    tmp.concat(workflows.splice(i+1));
                    workflows = tmp;
                    break;
                }
            }
            removeWorkflow(value);
        }
        workflows = JSON.stringify(workflows);
        $.cookie('workflows', workflows)
    });

    var addWorkflow = function(workflow) {
        url = "/workflow/"+workflow+"/rendered";
        $.get(url, function(res) {
            var parser = new DOMParser()
            var parsed = parser.parseFromString(res, "text/html")
            divId = ""+workflow
            var div = parsed.getElementById(divId)
            outer_div = document.getElementById("accordion")
            outer_div.appendChild(div);
        });
    };
    var removeWorkflow = function(workflow) {
        workflow = "#"+workflow;
        $(workflow).remove();
    };

    var tc = document.getElementById("ticketContent");
    var tl = document.getElementById("ticketList");
    var hardTop = $(tl).offset().top;

    $(window).scroll(function() {
        var scrollTop = $(this).scrollTop();
        var diff = hardTop-scrollTop;

        if (diff < 20) {
            var currTop = $(tc).offset().top;
            diff = currTop-scrollTop;
            if (diff < 15) {
                lastTop = 15;
            } else {
                lastTop = diff;
            }
            $(tc).css("position", "fixed");
            $(tc).css("top", ""+lastTop+"px");
            $(tc).css("right", "10px");
        } else {
            lastTop = null;
            $(tc).css("position", "absolute");
            $(tc).css("top", "");
            $(tc).css("right", "10px");
        }
    });

    // refresh workflow panes
    var refresh = function() {
        $(".div_workflow").each(function(i, el) {
            var workflow = el.id;
            $.get('/workflow/'+workflow+'/rendered', function(res) {
                var parser = new DOMParser();
                var parsed = parser.parseFromString(res, "text/html");
                divId = ""+workflow
                var div = parsed.getElementById(divId);
                // preserve checked boxes
                $("input[type=checkbox]:checked", el).each(function(i, cb){
                    $("#"+cb.id, div).attr("checked", true)
                });
                // preserve active task
                $("tr.info", el).each(function(i, tr) {
                    $("#"+tr.id, div).addClass("info");
                });
                $(el).replaceWith(div);
            });
        });
    }

    setInterval(refresh, 10000)
});

var isWorkflowInCookie = function(workflow, cookieName) {
    var cookie = $.cookie(cookieName);
    if (typeof cookie !== "undefined" && cookie.trim() !== '""') {
        var fields = JSON.parse(cookie);
        return fields.indexOf(workflow) >= 0;
    }
    return false;
}

// show or hide specific tasks in a workflow
var showHide = function(el, type) {
    var div = $(el).closest("form").parent()[0];
    var workflow = div.id;
    // task pattern
    var pattern = "tr."+type;

    var cookieName = "workflows_hide_"+type;
    var cookie = $.cookie(cookieName);
    if (typeof cookie === "undefined" || cookie.trim() === '""') {
        $.cookie(cookieName, JSON.stringify([workflow]));
    } else {
        // is this workflow hidden? if so, we want to show it
        // otherwise, we want to hide it!
        var hidden = JSON.parse(cookie)
        var idx = hidden.indexOf(workflow);
        if (idx < 0) {
            // not currently hidden, so let's hide it!
            hidden.push(workflow);
            el.innerHTML="show "+type;
            $(pattern, div).each(function(i, el){
                $(el).toggle();
                // uncheck and disable hidden items so they're not submitted by surprise!
                $("input[type=checkbox]", el).attr("checked", false).addClass("inactive");
            });
        } else {
            // currently hidden, so let's show it!
            var above = hidden.splice(idx, hidden.length-idx);
            if (above.length > 1) {
                above.shift();
            } else {
                above = [];
            }
            hidden = hidden.concat(above);
            el.innerHTML="hide "+type;
            $(pattern, div).each(function(i, el){
                $(el).toggle();
                // re-enable
               $("input[type=checkbox]", el).attr("checked", false).removeClass("inactive");
            });
        }
        $.cookie(cookieName, JSON.stringify(hidden));
    }
}

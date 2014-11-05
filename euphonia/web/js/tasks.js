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

/**
 * Remove a task from the list
 * @param {string} task to act upon
 * @return {null}
 */
function removeTask(task) {
    var success = function(){
        var taskObj = $('#' + task);
        taskObj.hide(400);
        taskObj.find('.stats').hide();
        $('#' + task + '-remove').show();
    };
    taskAction(task,"remove",success,failure,0);
}

/**
 * Sleep a task in the list
 * @param {string} task to act upon
 * @param {int} seconds to sleep the task
 * @return {null}
 */
function sleepTask(task,seconds) {
    seconds = seconds || 0;
    var success = function(response){
        var taskObj = $('#' + task);
        taskObj.find('.stats').hide();
        if(seconds === 0){
            taskObj.addClass('frozen');
            taskObj.toggle(!$('.frozen').is(':visible'));
            $('#' + task + '-frozen').show();
        }
        replaceStartDate(task,JSON.parse(response).task.start.$date);
    };
    taskAction(task,"sleep",success,failure,seconds);
}

/**
 * Wake a task on the list
 * @param {string} task to act upon
 * @return {null}
 */
function wakeTask(task) {
    var success = function(response){
        $('#' + task).removeClass('frozen');
        $('#' + task + '-frozen').hide();
        replaceStartDate(task,JSON.parse(response).task.start.$date);
    };
    taskAction(task,"wake",success,failure,0);
}

/**
 * Approve a task on the list
 * @param {string} task to act upon
 * @return {null}
 */
function approveTask(task) {
    var success = function(){
        var taskObj = $('#' + task);
        taskObj.find('.approve').toggle();
        taskObj.find('.stats').hide();
        $('#' + task + '-approve').show();
    };
    taskAction(task,"approve",success,failure,0);
}

/**
 * Disapprove a task on the list
 * @param {string} task to act upon
 * @return {null}
 */
function disapproveTask(task) {
    var success = function(){
        var taskObj = $('#' + task);
        taskObj.find('.approve').toggle();
        taskObj.find('.stats').hide();
    };
    taskAction(task,"disapprove",success,failure,0);
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
    window.setTimeout(function(){window.location.href = window.location.href;},60000);
});
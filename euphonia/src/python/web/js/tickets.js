
function showPage(context, url, issue) {
    $('#ticketList').find('tr').each(function(){$(this).removeClass('info');});
    $(context).closest('tr').addClass('info')
    $('#ticketFrame').attr('src','');
    $('#ticketFrame').attr('src',url);
    $('#ticketLink').attr('href',url);
    $('#ticketList').addClass('col-lg-6');
    $('#ticketList').removeClass('col-lg-12');
    $('#ticketTitle > span').text('Jira view of ' + issue);
    $('#ticketContent').addClass('col-lg-6');
    $('#ticketContent').height(Math.max($('#ticketList').height(),600));
    $('#ticketContent').show();
}

function closePage() {
    $('#ticketList').find('tr').each(function(){$(this).removeClass('info');});
    $('#ticketList').addClass('col-lg-12');
    $('#ticketList').removeClass('col-lg-6');
    $('#ticketContent').hide();
}

function failure(content){
    alert("unable to complete request");
}
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

function removeTask(task) {
    success = function(response){
        $('#' + task).hide(400);
        $('#' + task).find('.stats').hide();
        $('#' + task + '-remove').show();
    };
    taskAction(task,"remove",success,failure);
}

function sleepTask(task,seconds) {
    seconds = seconds || 0;
    success = function(response){
        $('#' + task).find('.stats').hide();
        if(seconds == 0){
            $('#' + task).addClass('frozen');
            $('#' + task).toggle(!$('.frozen').is(':visible'));
            $('#' + task + '-frozen').show();
        }
        replaceStartDate(task,JSON.parse(response)['task']['start']['$date']);
    };
    taskAction(task,"sleep",success,failure,seconds);
}

function wakeTask(task) {
    success = function(response){
        $('#' + task).removeClass('frozen');
        $('#' + task + '-frozen').hide();
        replaceStartDate(task,JSON.parse(response)['task']['start']['$date']);
    };
    taskAction(task,"wake",success,failure);
}

function approveTask(task) {
    success = function(response){
        $('#' + task).find('.approve').toggle();
        $('#' + task).find('.stats').hide();
        $('#' + task + '-approve').show();
    };
    taskAction(task,"approve",success,failure);
}

function disapproveTask(task) {
    success = function(response){
        $('#' + task).find('.approve').toggle();
        $('#' + task).find('.stats').hide();
    };
    taskAction(task,"disapprove",success,failure);
}

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

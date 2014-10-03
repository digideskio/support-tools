$(document).ready(function() {
    $(document).bind('keydown', '/', function () {
        if ($("input,textarea").is(":focus")) {
            return true;
        } else {
            $('#groupSearch').focus();
            return false;
        }
    });
    $('.failedtests').popover();
    $('.tooltip').tooltip();
    $('.metadata').tooltip();
    $('.tt-input').focus(function() {
        $('.twitter-typeahead').width(300);
    }).blur(function() {
       $('.twitter-typeahead').width(150);
    });
});

var groups = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.whitespace('GroupName'),
  queryTokenizer: Bloodhound.tokenizers.whitespace,
  remote: '/search/%QUERY'
});

groups.initialize();

suggestionTemplate = Handlebars.compile('<p><a href="/group/{{GroupId}}"><strong>{{GroupName}}</strong></a></p>');

$('#groupSearch').typeahead(
    {
        hint: true,
        highlight: true,
        minLength: 3
    },
    {
        name: 'autocomplete',
        source: groups.ttAdapter(),
        displayKey: 'GroupName',
        templates: {
            empty: '<div>No matches found...</div>',
            suggestion: suggestionTemplate
        }
    }
).bind("typeahead:selected", function (obj,datum){
	window.location = "/group/" + datum.GroupId;
}).keypress(function (e) {
  if (e.which == 13) {
    return false;
  }
});

function showPage(context, url, issue) {
    $('#ticketList').find('tr').each(function(){$(this).removeClass('info');});
    $(context).closest('tr').addClass('info')
    $('#ticketFrame').attr('src','');
    $('#ticketFrame').attr('src',url);
    $('#ticketList').addClass('col-lg-6');
    $('#ticketList').removeClass('col-lg-12');
    $('#ticketTitle > span').text('Jira view of ' + issue);
    $('#ticketContent').addClass('col-lg-6');
    $('#ticketContent').height(Math.max($('#ticketList').height(),600));
    $('#ticketContent').show();
    //$('#ticketFrame').height(Math.max($('#ticketList').height() - 100,550));
    //$('#ticketFrame').width($('#ticketList').width() - 30);
}

function closePage() {
    $('#ticketList').find('tr').each(function(){$(this).removeClass('info');});
    $('#ticketList').addClass('col-lg-12');
    $('#ticketList').removeClass('col-lg-6');
    $('#ticketContent').hide();
}
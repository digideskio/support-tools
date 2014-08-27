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
    $('.collapse').collapse();
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
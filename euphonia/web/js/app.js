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

    // If auth_token is set, use it to initialize
    // user profile
    initFromAuthToken();

    // Login, i.e. set auth_token
    $('#nav_a_login').click(function() {
        var auth_token = prompt("auth_token:");
        $.cookie('auth_token', auth_token)
        initFromAuthToken();
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

var initFromAuthToken = function() {
    var auth_token = $.cookie('auth_token');
    if (typeof auth_token !== "undefined") {
        var urlString = "/login";
        var data = {'auth_token': auth_token};
        $.post(urlString, data, function(res){
            name = res['data']['user']
            profileImageUrl = "https://corp.10gen.com/employees/" + name + "/profileimage";
            var img = document.createElement("img");
            img.src = profileImageUrl;
            img.id = "img_profile";
            $("#nav_a_login").css('padding', 0)
                             .css('margin', 0)
                             .html(img)
        }, "json");
    }
    return null;
}

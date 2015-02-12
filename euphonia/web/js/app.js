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

    userInit();

    // Login, i.e. set kk_token
    $('#nav_a_login').click(function() {
        var auth_token = prompt("kk_token:");
        deleteCookies();
        $.cookie('kk_token', auth_token);
        var callback = function() {window.location.reload()};
        initFromAuthToken(callback);
    });
});

var deleteCookies = function() {
    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i++) {
        name = cookies[i].split('=')[0]
        $.removeCookie(name);
    }
}

var groups = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.whitespace('GroupName'),
  queryTokenizer: Bloodhound.tokenizers.whitespace,
  remote: '/search/%QUERY'
});

groups.initialize();

var suggestionTemplate = Handlebars.compile('<p><a href="/group/{{GroupId}}"><strong>{{GroupName}}</strong></a></p>');

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

var userInit = function() {
    var user = $.cookie('user');
    if (user) {
        var name = unescape(user);
        var profileImageUrl = "https://corp.10gen.com/employees/" + name + "/profileimage";
        var img = document.createElement("img");
        img.src = profileImageUrl;
        img.id = "img_profile";
        $("#nav_a_login").css('padding', 0)
                         .css('margin', 0)
                         .html(img);
    } else {
        initFromAuthToken();
    }
}

var initFromAuthToken = function(callback) {
    var auth_token = $.cookie('kk_token');
    if (typeof auth_token !== "undefined") {
        var urlString = "/login";
        var data = {'auth_token': auth_token};
        $.post(urlString, data).always(function() {
            if (typeof callback !== "undefined"){
                return callback();
            }
        });
    }
};

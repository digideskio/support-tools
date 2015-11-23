
function open_current(default_cmdline) {
    var p = 'Open new view in current window. Use timeseries command-line syntax to specify:'
    specs = prompt(p, default_cmdline)
    if (specs) {
        url = '?args=' + encodeURI(specs)
        load_content(url)
    }
}

function open_new(default_cmdline) {
    var p = 'Open new view in a new window. Use timeseries command-line syntax to specify:'
    specs = prompt(p, default_cmdline)
    if (specs) {
        url = '/open?args=' + encodeURI(specs)
        url = absoluteURL(url)
        window.open(url)
    }
}

// hack to get absolute url from relative
function absoluteURL(url) {
    var a = document.createElement('a');
    a.href = url;
    return a.href;
}

// not used?
function do_request(method, url, model) {
    form = document.createElement("form");
    form.action = url;
    form.method = method
    items = ['after', 'before', 'level', 'cursors']
    function one(n, v) {
        e = document.createElement("input");
        e.name = n
        e.value = v
        form.appendChild(e)
    }
    for (i in items) {
        name = items[i]
        value = model[name]
        if (typeof(value)=='object') {
            for (var v in value)
                one(name, value[v])
        } else {
            one(name, value)
        }
    }
    form.submit()
}

// post variables (e.g. model) to url, then perform a function (e.g reload)
function do_post(url, vars, done) {

    // xxx general enough?
    url = top.location + '/' + url

    // create request
    req = new XMLHttpRequest()
    req.open('POST', url)
    req.setRequestHeader("Content-type", "application/json");

    // execute done() when finished
    if (done) {
        req.onreadystatechange = function() {
            if (req.readyState==4)
                done()
        }
    }

    // serialize as JSON and send
    function replacer(key, value) {
        return value!=null && typeof(value)=='object' && 'toJSON' in value? value.toJSON() : value
    }
    json = JSON.stringify(vars, replacer)
    req.send(json)
}

function load_content(args) {
    console.log('load_content()')
    if (top.live_timeout)
        clearTimeout(top.live_timeout)
    frameset = top.document.getElementById('frameset')
    if (!frameset.loading)
        frameset.loading = 0
    frameset.loading = 1 - frameset.loading
    frameset.rows = frameset.loading==0? '0%, 90%, 10%' : '90%, 0%, 10%'
    frameset.setAttribute('border', '1')
    progress = top.document.getElementById('progress')
    progress.innerHTML = ''
    progress.src = top.document.location + '/progress' + (args? args : '')
}

function loaded_progress() {
    console.log('loaded_progress()')
    frameset = top.document.getElementById('frameset')
    contents = top.document.getElementsByName('content')
    contents[frameset.loading].src = top.document.location + '/content'
}

function loaded_content() {
    console.log('loaded_content()')
    if (!top.model) {
        setTimeout(function(){open_current('ftdc:diagnostic.data')}, 1)
        return
    }
    initialize_model()
    frameset = top.document.getElementById('frameset')
    frameset.rows = frameset.loading==0? '100%, 0%, 0%' : '0%, 100%, 0%' 
    frameset.setAttribute('border', '0')
    contents = top.document.getElementsByName('content')
    contents[frameset.loading].focus()
    console.log('top.model.live', top.model.live)
    if (top.model.live > 0)
        top.live_timeout = setTimeout(post_model_and_load_content, top.model.live*1000)
}


function zoom() {

    // construct default zoom range using first and last cursor
    cs = top.model.cursors
    if (cs.length==0) {
        alert('First select a zoom range by clicking on the graph to place one or more cursors')
        return
    }  else if (cs.length==1) {
        range = cs[0].letter.innerHTML + '-'
    } else {
        range = cs[0].letter.innerHTML + '-' + cs[cs.length-1].letter.innerHTML
    }

    // allow user to override zoom range
    range = prompt('Zoom range:', range)

    // get positions for requested zoom range
    range = range.split(/[^A-Za-z]/, 2)
    function get_time(spec, deflt) {
        if (spec=='') {
            return deflt
        } else {
            var t = cursor2t(spec)
            if (t==undefined)
                alert('No such cursor: ' + spec)
            return t
        }
    }
    after = get_time(range[0], -1/0)
    before = get_time(range[1], 1/0)
    if (after==undefined || before==undefined)
        return;
    top.model['after'] = after
    top.model['before'] = before
    post_model_and_load_content()
}

function zoom_all() {
    if (confirm('Zoom out to show all data?')) {
        top.model.after = null
        top.model.before = null
        post_model_and_load_content()
    }
}

function info(raw) {

    // default cursor is last one
    cs = top.model.cursors
    if (cs.length==0) {
        alert('First place a cursor by clicking on the graph')
        return
    }
    cursor = cs[cs.length-1].letter.innerHTML

    // allow user to specify cursor
    cursor = prompt('Info for cursor:', cursor)

    // get time for requested cursor
    var t = cursor2t(cursor)
    if (t==undefined) {
        alert('No such cursor: ' + c)
        return
    }

    // load info for that time into info window
    q = raw? 'raw' : 'info'
    url = top.location + '/' + q + '?t=' + t
    top.open(url, 'info')
}

function post_model_and_load_content() {
    if (top.model) {
        console.log('posting', top.model)
        top.model.scrollY = window.scrollY
        do_post('model', top.model, load_content)
    } else {
        console.log('no model, not posting')
        load_content()
    }
}


        

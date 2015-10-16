var selected = undefined
var last_selected = undefined

function _desel() {
    if (selected)
        selected.classList.remove('selected')
}

function _sel(s) {
    if (selected) {
        last_selected = selected
        selected.classList.add('selected')
        for (var p=selected, y=0; p && p.tagName!='BODY'; p=p.offsetParent)
            y += p.offsetTop
        var h = selected.offsetHeight
        if (window.pageYOffset + window.innerHeight < y + h)
            selected.scrollIntoView(false)
        else if (y < window.pageYOffset)
            selected.scrollIntoView(true)
    }
}

function sel(e) {
    _desel()
    if (selected!=e) {
        selected = e
        _sel()
    } else {
        selected = undefined
    }
}

function re_number() {
    n = 0
    row = document.getElementById("table").firstChild.firstChild    
    while (row) {
        td = row.firstChild
        while (td && !td.classList.contains("row-number"))
            td = td.nextSibling            
        if (!td)
            return
        if (!td.classList.contains("head")) {
            td.innerHTML = n
            n += 1
        }
        row = row.nextSibling
    }
}

function set_level(level) {
    _desel()
    row = document.getElementById("table").firstChild.firstChild    
    while (row) {
        row_level = Number(row.getAttribute('_level'))
        if (row_level <= level) {
            row.style.display = ''
        } else {
            row.style.display = 'none'
        }
        row = row.nextSibling
    }
    document.getElementById("current_level").innerHTML = String(level)
    selected = next_visible(selected)
    model.level = level
}

function initialize_model() {
    set_level(model.level)
    add_cursors_by_time(model.cursors)
}

function next_visible(row) {
    while (row && row.style.display=='none')
        row = row.nextSibling
    return row            
}

function prev_visible(row) {
    while (row!=first_row && row.style.display=='none')
        row = row.previousSibling
    return row            
}

function key() {
    var evt = window.event
    var c = String.fromCharCode(evt.charCode)
    first_row = document.getElementById("table").firstChild.firstChild
    while (first_row && !first_row.classList.contains('row'))
        first_row = first_row.nextSibling
    first_row = next_visible(first_row)
    if (!last_selected) {
        for (var r = first_row; r && !selected; r = r.nextSibling) {
            if (r.classList.contains('selected'))
                selected = r
        }
        last_selected = selected
    }
    if (!last_selected)       
        last_selected = first_row
    if (c=='s') {
        fn = prompt('Save to file:', 'timeseries.html')
        if (fn)
            do_post('save', {fn: fn})
    } else if (c=='z') {
        zoom()
    } else if (c=='Z') {
        zoom_all()
    } else if (c=='') {
        if (!selected)
            selected = last_selected
        else {
            var s = next_visible(selected.nextSibling)
            if (s) {
                _desel()
                selected = s
            }
        }
    } else if (c=='') {
        if (!selected)
            selected = last_selected
        else if (selected != first_row) {
            selected.classList.remove('selected')
            selected = prev_visible(selected.previousSibling)
        }
    } else if (c=='n') {
        if (selected) {
            next = next_visible(selected.nextSibling)
            if (next) {
                parent = selected.parentNode
                parent.removeChild(selected)
                parent.insertBefore(selected, next.nextSibling)
                re_number()
            }
        }
    } else if (c=='p') {
        if (selected) {
            if (selected!=first_row) {
                prev = prev_visible(selected.previousSibling)
                parent = selected.parentNode
                parent.removeChild(selected)
                parent.insertBefore(selected, prev)
                re_number()
            }
        }
    } else if (c=='N') {
        if (selected) {
            s = next_visible(selected.nextSibling)
            if (s) {
                parent = selected.parentNode
                parent.removeChild(selected)
                parent.insertBefore(selected, null)
                sel(s)
                re_number()
            }
        }
    } else if (c=='P') {
        if (selected && selected != first_row) {
            s = prev_visible(selected.previousSibling)
            parent = selected.parentNode
            parent.removeChild(selected)
            parent.insertBefore(selected, first_row)
            sel(s)
            re_number()
        }
    } else if ('1'<=c && c<='9') {
        set_level(Number(c))
        do_post('model', model)
    } else if (c=='o') {
        var p = 'Open new view in current window. Use timeseries command-line syntax to specify:'
        specs = prompt(p, model.spec_cmdline)
        url = '/open?args=' + encodeURI(specs)
        window.location.href = url
    } else if (c=='O') {
        var p = 'Open new view in a new window. Use timeseries command-line syntax to specify:'
        specs = prompt(p, model.spec_cmdline)
        url = '/open?args=' + encodeURI(specs)
        url = absoluteURL(url)
        window.open(url)
    }
    _sel(selected)
}    



// hack to get absolute url from relative
function absoluteURL(url) {
    var a = document.createElement('a');
    a.href = url;
    return a.href;
}

function toggle_help() {
    e = document.getElementById('help')
    if (e.style.display == 'none') {
        e.style.display = 'block'
    } else {
        e.style.display = 'none'
    }
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
    url = window.location + '/' + url

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


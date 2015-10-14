// x position of current event as a proportion (0-1) of the width of the containing element
function event_x(e) {
    var evt = window.event
    return (evt.pageX - e.offsetLeft - e.offsetParent.offsetLeft) / e.offsetWidth
}

var svg_ns = "http://www.w3.org/2000/svg"

function set_attrs(e, attrs) {
    for (a in attrs)
        e.setAttribute(a, attrs[a])
}

function elt(ns, name, attrs) {
    var e = document.createElementNS(ns, name)
    set_attrs(e, attrs)
    return e
}

function del_id(id) {
    var e = document.getElementById(id)
}

function move(e) {
    var x = event_x(e)
    set_attrs(document.getElementById('lll'), {x1:x, x2:x})
}

function out(e) {
    set_attrs(document.getElementById('lll'), {x1:-1, x2:-1})
}

// add a cursor at the position where mouse event e occurred
// all position computations are done relative to the width of the graphs
function add_cursor_by_event(evt) {
    var x = event_x(evt)
    _add_cursor(x)
    update_cursors()
    do_post('model', model)
}

// add a cursor at time t
// all position computations are done relative to the width of the graphs
function add_cursors_by_time(ts) {
    for (var i in ts)
        _add_cursor(t2x(ts[i]))
    update_cursors()
}

function _add_cursor(x) {
    var line = elt(svg_ns, "line", {
        x1:x, x2:x, y1:0, y2:1, class:"cursor"
    })
    var deleter = elt(svg_ns, "circle", {
        cx:(x*100)+'%', cy:'50%', r:0.3, class:"deleter", onclick:"del_cursor_event(this)"
    })
    var letter = elt(svg_ns, "text", {
        x:(x*100)+'%', y:'80%', 'text-anchor':'middle', 'class':'letter'
    })
    cursor = {line: line, deleter: deleter, letter: letter, t: x2t(x), x: x}
    cursor.toJSON = function() {return this.t} // serialize for sending to server
    line.cursor = cursor
    deleter.cursor = cursor
    letter.cursor = cursor
    document.getElementById("cursors").appendChild(line)
    document.getElementById("deleters").appendChild(deleter)
    document.getElementById("letters").appendChild(letter)
    update_cursors()
}

function del_cursor_event(deleter) {
    cursor = deleter.cursor;
    ['line', 'deleter', 'letter'].forEach(function(n){
        e = cursor[n]
        e.parentNode.removeChild(e)
    })
    update_cursors()
    do_post('model', model)    
}

function update_cursors() {
    cursors = []
    deleters = document.getElementById("deleters")
    for (var i=0; i<deleters.children.length; i++)
        cursors.push(deleters.children[i].cursor)
    cursors.sort(function(a,b) {return a.x-b.x})
    for (var i=0; i<cursors.length; i++)
        cursors[i].letter.innerHTML = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijlkmnopqrstuvwxyz'[i]
    model.cursors = cursors
}

// position of an element on the graph; units are %
function pos(e) {
    return Number(e.getAttribute('x').replace('%',''))
}

// x is a relative position (0-1) within the graphing area, which includes xpad on either side
// compute the corresponding time on the graph, given tleft and tright supplied by server
function x2t(x) {
    return model.tleft * (1-x) + model.tright * x
}

function t2x(t) {
    return (t-model.tleft) / (model.tright-model.tleft)
}

function zoom() {

    // construct default zoom range using first and last cursor
    cs = model.cursors
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
    function get_time(spec, attr) {
        var t = null
        if (spec.length==1) {
            for (var j in cs) {
                if (cs[j].letter.innerHTML==spec) {
                    t = cs[j].t
                    break
                }
            }
            if (t==undefined) {
                alert('No such cursor: ' + c)
                return
            }
        }
        model[attr] = t
    }
    get_time(range[0], 'after')
    get_time(range[1], 'before')
    do_post('model', model, function(){window.location.reload(true)})
}

function zoom_all() {
    if (confirm('Zoom out to show all data?')) {
        model.after = null
        model.before = null
        do_post('model', model, function(){window.location.reload(true)})
    }
}

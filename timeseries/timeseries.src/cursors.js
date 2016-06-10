// x position of current event as a proportion (0-1) of the width of the containing element
function event_x(e) {
    var evt = window.event
    r = e.getBoundingClientRect()
    return (evt.pageX - r.left) / r.width
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
}

function update_cursors() {
    cursors = []
    deleters = document.getElementById("deleters")
    for (var i=0; i<deleters.children.length; i++)
        cursors.push(deleters.children[i].cursor)
    cursors.sort(function(a,b) {return a.x-b.x})
    for (var i=0; i<cursors.length; i++)
        cursors[i].letter.innerHTML = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijlkmnopqrstuvwxyz'[i]
    top.model.cursors = cursors
}

// position of an element on the graph; units are %
function pos(e) {
    return Number(e.getAttribute('x').replace('%',''))
}

// x is a relative position (0-1) within the graphing area, which includes xpad on either side
// compute the corresponding time on the graph, given tleft and tright supplied by server
function x2t(x) {
    return top.model.tleft * (1-x) + top.model.tright * x
}

function t2x(t) {
    return (t-top.model.tleft) / (top.model.tright-top.model.tleft)
}

// get time at cursor, specified by cursor letter
function cursor2t(cursor) {
    var cs = top.model.cursors
    for (var j in cs)
        if (cs[j].letter.innerHTML==cursor)
            return cs[j].t
    return undefined
}


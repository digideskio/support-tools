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
function add(e) {
    var x = event_x(e)
    var cursor = elt(svg_ns, "line",
                     {x1:x, x2:x, y1:0, y2:1, class:"cursor"})
    var deleter = elt(svg_ns, "circle",
                      {cx:(x*100)+'%', cy:'50%', r:0.3, class:"deleter", onclick:"del(this)"})
    var letter = elt(svg_ns, "text",
                     {x:(x*100)+'%', y:'80%', 'text-anchor':'middle', 'class':'letter'})
    document.getElementById("cursors").appendChild(cursor)
    document.getElementById("deleters").appendChild(deleter)
    document.getElementById("letters").appendChild(letter)
    deleter.related = [deleter, cursor, letter]
    re_letter()
}

function del(deleter) {
    for (var i in deleter.related) {
        e = deleter.related[i]
        e.parentNode.removeChild(e)
    }
    re_letter()
}

function pos(e) {
    return Number(e.getAttribute('x').replace('%',''))
}

function get_letters() {
    ls = []
    letters = document.getElementById("letters")
    for (var i=0; i<letters.children.length; i++) {
        child = letters.children[i]
        if (child.classList.contains('letter')) {
            //console.log(child.getAttribute('x') + ' ' + child.innerHTML)
            ls.push(child)
        }
    }
    return ls.sort(function(a,b) {return pos(a)-pos(b)})
}

function re_letter() {
    console.log('re_letter')
    var ls = get_letters()
    for (var i in ls)
        ls[i].innerHTML = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijlkmnopqrstuvwxyz'[i]
}

function zoom() {

    // construct default zoom range using first and last cursor
    var ls = get_letters()
    if (ls.length==0) {
        alert('First select a zoom range by clicking on the graph to place one or more cursors')
        return
    }  else if (ls.length==1) {
        range = ls[0].innerHTML + '-end'
    } else {
        range = ls[0].innerHTML + '-' + ls[ls.length-1].innerHTML
    }

    // allow user to override zoom range
    prompt('Zoom range:', range)

    // get positions for requested zoom range
    range = range.split(/[^A-Za-z]/, 2)
    var ls = get_letters()
    for (var i in range) {
        var c = range[i]
        if (c.length==1) {
            var x = undefined
            for (var j in ls) {
                if (ls[j].innerHTML==c) {
                    range[i] = pos(ls[j]) / 100.0
                    break
                }
            }
            if (range[i]==undefined) {
                alert('No such cursor: ' + c)
                return
            }
        } else if (c=='end' || c=='start') {
            range[i] = c
        } else {
            alert('Don\'t understand "' + c + '"')
            return
        }
    }

    // submit post request (defined in html.js)
    post("/zoom", {start: range[0], end: range[1]})
}

function zoom_all() {
    if (confirm('Zoom out to show all data?'))
        post('/zoom', {start: 'all', end: 'all'})
}

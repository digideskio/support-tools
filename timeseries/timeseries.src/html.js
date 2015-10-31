var selected = undefined
var last_selected = undefined

function _desel() {
    if (selected)
        selected.classList.remove('selected')
}

// process change to selected
function _sel() {

    if (selected) {

        // record selected row
        _row = selected.getAttribute('_row')
        if (_row)
            top.model.selected = Number(_row)

        // compute last_selected
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

// select e, deselect current selection
function sel(e) {
    _desel()
    if (selected!=e) {
        selected = e
        _sel()
    } else {
        selected = undefined
    }
}

// set selected to the specified row
function set_selected(_row) {
    if (_row != undefined) {
        row = document.getElementById("table").firstChild.firstChild    
        while (row) {
            if (_row==row.getAttribute('_row')) {
                selected = row
                _sel()
                break
            }
            row = row.nextSibling
        }
    }
}

function re_number() {
    console.log('re_number()')
    n = 0
    row = document.getElementById("table").firstChild.firstChild    
    top.model.row_order = []
    while (row) {
        _row = row.getAttribute('_row')
        if (_row)
            top.model.row_order.push(Number(_row))
        row = row.nextSibling
    }
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
    top.model.level = level
}

function initialize_model() {
    console.log('initializing', top.model)
    set_level(top.model.level)
    set_selected(top.model.selected)
    if (top.model.scrollY != undefined)
        window.scrollTo(0, top.model.scrollY)
    add_cursors_by_time(top.model.cursors)
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

    // compute last_selected
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
        _sel()
    } else if (c=='') {
        if (!selected)
            selected = last_selected
        else if (selected != first_row) {
            selected.classList.remove('selected')
            selected = prev_visible(selected.previousSibling)
        }
        _sel()
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
        _sel()
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
        _sel()
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
        _sel()
    } else if (c=='P') {
        if (selected && selected != first_row) {
            s = prev_visible(selected.previousSibling)
            parent = selected.parentNode
            parent.removeChild(selected)
            parent.insertBefore(selected, first_row)
            sel(s)
            re_number()
        }
        _sel()
    } else if ('1'<=c && c<='9') {
        set_level(Number(c))
        _sel()
    } else if (c=='o') {
        open_current(top.model.spec_cmdline)
    } else if (c=='O') {
        open_new(top.model.spec_cmdline)
    } else if (c=='l') {
        default_live = top.model.live>0? top.model.live : 10
        live = prompt('Refresh interval in seconds; 0 to disable:', default_live)
        if (live) {
            top.model.live = Number(live)
            if (top.model.live > 0)
                load_content()
        }
    }
}    

function toggle_help() {
    e = document.getElementById('help')
    if (e.style.display == 'none') {
        e.style.display = 'block'
    } else {
        e.style.display = 'none'
    }
}

function loaded_content() {
    initialize_model()
}

function do_post() {
    console.log('not posting')
}

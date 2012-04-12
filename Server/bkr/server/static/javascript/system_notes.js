$(document).ready(function() {
    $("a[id^='delete_note_']").click(function() {
        var element_id = $(this).attr('id')
        var id_regex = /delete_note_(\d+)/
        var id = element_id.replace(id_regex, "$1")
        var callback = on_complete(id)
        do_and_confirm('../delete_note',{'id':id}, callback, undefined, 'delete')
    });

});

function on_complete (element_id) {

    return function(success) {
        if (!success) {
            note_delete_failure()
        } else {
            note_delete_success(element_id)
        }
    }
}

function note_delete_failure () {
    failure('Could not delete note please contact your administrator')
}

function note_delete_success(id) {

    //Test to see if we are currently showing deleted notes
    var hide = true
    var deleted_elem = $("tbody[id^='note_deleted_']").first()
    if (deleted_elem.length != 0) {
        // If deleted_elems are displayed, don't hide.
        if (deleted_elem.css('display') != 'none') {
            hide = false
        }
    }

    if (hide) {
        $("tbody[id='note_" + id +"']").fadeOut(1000);
    }

    $("tbody[id='note_" + id +"']").attr('id', 'note_deleted_' + id);
    var toggle_notes = $('#toggle_deleted_notes')
    var toggle_notes_display = toggle_notes.css('display')
    if (toggle_notes_display == 'none') {
        toggle_notes.css('display', 'inline')
    }
    $('#delete_note_' + id).remove();
}


function toggle_deleted_notes() {
    $("tbody[id^='note_deleted']").toggle()
}

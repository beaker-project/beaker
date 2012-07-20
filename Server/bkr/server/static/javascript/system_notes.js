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

function note_delete_success(id) {

    //Test to see if we are currently showing deleted notes
    var hide = true
    var deleted_elem = $(".note_deleted").first();
    if (deleted_elem.length != 0) {
        // If deleted_elems are displayed, don't hide.
        if (deleted_elem.css('display') != 'none') {
            hide = false
        }
    }

    if (hide) {
        $("tr[id='note_" + id +"']").fadeOut(1000);
    }

    $("tr[id='note_" + id +"']").addClass('note_deleted');
    var toggle_notes = $('#toggle_deleted_notes')
    var toggle_notes_display = toggle_notes.css('display')
    if (toggle_notes_display == 'none') {
        toggle_notes.css('display', 'inline')
    }
    $('#delete_note_' + id).remove();
}

function toggle_deleted_notes() {
    $(".note_deleted").toggle();
}

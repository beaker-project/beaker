function populate_form_elements (form) {
    // We have created hidden inputs with no value,
    var hiddens_need_value = $(form).children("input[type=hidden]").not("[value]")
    var get_names_of = []
    for (i=0; i < hiddens_need_value.length;i++) {
        var child = hiddens_need_value[i]
        var child_id = child.id
        var re = /^(.+)_hidden$/
        var real_input_id = child_id.replace(re,"$1")
        var visible_elem = $('#' + real_input_id)
        // Populate our hidden field with what's in the non hidden field
        child.value = visible_elem.val()
    }
}

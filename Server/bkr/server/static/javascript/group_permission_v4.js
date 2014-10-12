$(document).ready(function () {
    $(document).on('click', 'a[id ^="remove_permission_"]', function () {
        var elem_id = $(this).attr('id')
        var group_permission_id = elem_id.replace(/remove_permission_(\d+)$/,"$1")
        group_permission_remove(group_permission_id)
        return false;
    });
});

function add_group_permission_success (result) {
    var result = $.parseJSON(result)
    var added_permission_name = result['name']
    var added_permission_id = result['id']
    var added_permission_tr = $("<tr></tr>");
    var td_permission = $("<td></td>").text(added_permission_name)
    var a_remove = $("<a></a>").attr('id', 'remove_permission_' + added_permission_id)
    a_remove.html('<i class="fa fa-times"></i> Remove');
    a_remove.addClass('btn');
    var td_remove = $("<td></td>").html(a_remove)
    added_permission_tr.append(td_permission).append(td_remove)
    //Add the new group permission row
    $('#' + permissions_grid_id + ' tbody').append(added_permission_tr);
}

function group_permission_remove(permission_id) {

    function f(result) {
        group_permission_remove_result(result, permission_id)
    }

    do_and_confirm_ajax('remove_group_permission',
        {'group_id': group_id , 'permission_id': permission_id },f, undefined, 'remove')
}

function group_permission_remove_result(result, permission_id) {
    if (result == false) {
        update_results({'text':'Error removing group permission',
            'success':false} )
    } else {
        var tr_to_remove = $('#remove_permission_' + permission_id ).parent().parent()
        tr_to_remove.detach()
    }
}

function add_group_permission_failure (error) {
    update_results({'text':error, 'success':false} )
}

function before_group_permission_submit() {
    AjaxLoader.prototype.add_loader(permissions_form_id)
}

function after_group_permission_submit() {
    AjaxLoader.prototype.remove_loader(permissions_form_id)
}

function update_results (result) {
    AjaxLoader.prototype.remove_loader(permissions_form_id)
    var success = result['success']
    var text = null

    if (result['text']) {
        text = result['text']
    }

    if (success) {
        if (!text) {
            text = 'Success'
        }
        colour = '#00FF00'
        response_type = 'success'
    } else {
        if (!text) {
            text = 'Error updating'
        }
        colour = '#FF0000'
        response_type = 'failure'
    }

    if ($("span[id^='response_"+permissions_form_id+"']").length) {
        return_msg = $("span[id^='response_"+permissions_form_id+"_']").text(text)
        return_msg.fadeIn("slow")
        return_msg.delay(5000).fadeOut(1000)

    } else {
        var return_msg = $("<span></span>").html(text).css('background-color',colour).css('display','inline-block').css('margin','1em 0 0 2em').attr('id','response_'+permissions_form_id+'_'+response_type).addClass('rounded-side-pad')
        $('#'+permissions_form_id).before(return_msg).fadeIn("slow")
        return_msg.delay(5000).fadeOut(1000)
    }
}



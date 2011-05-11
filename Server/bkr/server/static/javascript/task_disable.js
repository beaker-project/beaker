function task_disable_decide(action,data) {
    var newpara = $('<p></p>').text('Are you sure you want to disable task?')
    var dialog_div = $('<div></div>').attr('title','Disable').append(newpara)

    dialog_div.dialog({
        resizable: false,
        height:200,
        modal: true,
        buttons: {
            "Disable": function() {
                $( this ).dialog( "close" );
                do_disable(action,data)
                },
            Cancel: function() {
                $( this ).dialog( "close" );
                }
            }
    });
}


function do_disable(action,data) {
    var d = loadJSONDoc(action + "?" + queryString(data))
    d.addCallback(do_task_disable_complete)
}


function task_disable_success(t_id) {
    //remove the row from the list
    $("a[t_id='"+ t_id + "']").parents('tr').fadeOut(1000, function() { $(this).remove() });
}


function task_disable_failure(err_msg, t_id) {
    //show error message
    msg_to_show = 'There was a problem disabling your task ' + t_id +'. ';
    if (err_msg) {
        msg_to_show += "The error message returned was: '" + err_msg + "'";
    }
    var newpara = $('<p></p>').text(msg_to_show)
    var dialog_div = $('<div></div>').attr('title','Error').append(newpara);

    dialog_div.dialog({
        resizable: true,
        height: 250,
        width: 380,
        modal: true,
        buttons: {
            Ok: function() {
                $( this ).dialog( "close" );
                }
            }
    });
}


function do_task_disable_complete(result) {
    if (result['success']) {
        task_disable_success(result['t_id'])
    } else {
        task_disable_failure(result['err_msg'], result['t_id'])
    }
}


function TaskDisable(action, data, options) {
    task_disable_decide(action,data)
}

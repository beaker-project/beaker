function job_delete_decide(action,data) {
    var newpara = $('<p></p>').text('Are you sure you want to perform delete?')
    var dialog_div = $('<div></div>').attr('title','Delete').append(newpara)

    dialog_div.dialog({
        resizable: false,
        height:200,
        modal: true,
        buttons: {
            "Delete": function() {
                $( this ).dialog( "close" );
                do_delete(action,data)
                },
            Cancel: function() {
                $( this ).dialog( "close" );
                }
            }
    });
}


function do_delete(action,data) {
    var d = loadJSONDoc(action + "?" + queryString(data))
    d.addCallback(do_job_delete_complete)
}




function job_delete_failure(err_msg, t_id) {
    //show error message
    msg_to_show = 'There was a problem deleting your task ' + t_id +'. ';
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


function do_job_delete_complete(result) {
    if (result['success']) {
        job_delete_success(result['t_id'])
    } else {
        job_delete_failure(result['err_msg'], result['t_id'])
    }
}


function JobDelete(action, data, options) {
    job_delete_decide(action,data)
}

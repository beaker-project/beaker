function failure(err_msg) {
    //show error message
    var newpara = $('<p></p>').text(err_msg)
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

function delete_and_confirm(action, data, callback, msg) {
    var newpara = $('<p></p>').text('Are you sure you want to delete this?')
    var dialog_div = $('<div></div>').attr('title','Delete').append(newpara)

    dialog_div.dialog({
        resizable: false,
        height:200,
        modal: true,
        buttons: {
            "Delete": function() {
                $( this ).dialog( "close" );
                do_action(action,data,callback)
                },
            Cancel: function() {
                $( this ).dialog( "close" );
                }
            }
    });
}

function do_action(action,data,callback) {
    var d = loadJSONDoc(action + "?" + queryString(data))
    d.addCallback(callback)
}

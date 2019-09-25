function failure(err_msg) {
    //show error message
    var newpara = $('<p></p>').text("Your request failed with the following error: " + err_msg)
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

function do_and_confirm_form(msg, action_type, yes_action) {
    _do_and_confirm(false, null, {}, null, msg, action_type, yes_action);
}

function do_and_confirm_ajax(url, data, callback, msg, action_type) {
    _do_and_confirm(true, url, data, callback, msg, action_type, null);
}

function _do_and_confirm(ajax, url, data, callback, msg, action_type, yes_action) {
    if (! msg) {
        msg = 'Are you sure you want to '+ action_type +' this?'
    }
    var newpara = $('<p></p>').text(msg)
    var dialog_div = $('<div></div>').attr('title',action_type[0].toUpperCase() + action_type.slice(1,action_type.length)+' '+ (data.t_id || "")).append(newpara)

    if (! yes_action) {
        if (ajax == true) {
            yes_action = function() { do_action(url, data, callback) };
        }
    }

    dialog_div.dialog({
        resizable: false,
        height:200,
        modal: true,
        buttons: {
            "Yes": function() {
                $( this ).dialog( "close" );
                yes_action();
                },
            Cancel: function() {
                $(this).dialog("close");
            }
        }
    });
}

function success(msg) {
    var newpara = $('<p></p>').text(msg)
    var dialog_div = $('<div></div>').attr('title','Success').append(newpara)
    jQuery.fx.speeds._default = 2000;
        dialog_div.dialog({
            autoOpen: true,
            hide: "explode",
            resizable: false,
            height:195,
            modal: true,
            buttons: {
                Ok: function() {
                    $(this).dialog("close");
                }
            },
            open: function(event, ui) {
                $(this).oneTime(1000, function() {$(this).dialog("close")});
        }
    });
}

function post_error(response) {
    failure(response.responseText)
}

function do_action(action,data,callback) {
    data = queryString(data)
    jQuery.post(action, data, callback).error(post_error)
}

function show_field(id, title) {
    $('#'+id).attr('title', title).dialog({
            resizable: false,
            height: 300,
            width: 700,
            modal: true,});
}

function system_action_remote_form_request(form, options, action) {
    var query = formContents(form);
    query["tg_random"] = new Date().getTime();
    // Strip the form name from the options
    // otherwise it doesn't pass the args to the controller
    // in the correct format
    var stripped_query = []
    var form_names = query[0]
    for (counter in form_names) {
        stripped_query.push(form_names[counter].replace(/.+?\.(.+)$/, "$1"))
    }
    query[0] = stripped_query
    // Close our current form in anticipation of success/error dialog
    $('#' + form).dialog('close')
    // This is found in ajax.js
    remoteRequest(form, action, null, query, options);
    return true;
}

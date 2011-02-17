 function job_delete_success(t_id) {
    var newpara = $('<p></p>').text('Succesfully deleted '+ t_id)
    var dialog_div = $('<div></div>').attr('title','Success').append(newpara)
    jQuery.fx.speeds._default = 2000;
    dialog_div.dialog({
        autoOpen: true,
        hide: "explode",
        resizable: false,
        height:200,
        modal: true,
        open: function(event, ui) { 
            $(this).oneTime(1000, function() {$(this).dialog("close");$(location).attr('href','./mine')}); 
            }
    });
}


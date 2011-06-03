var has_watchdog = function(lc_id) {
    var params = {'id' : lc_id}
    // Change this to a template var
    var controller = './has_active_recipes'
    var d = loadJSONDoc(controller + '?' + queryString(params))
    d.addCallback(delete_lc, lc_id)
}

var delete_lc = function(lc_id, result) {
    if (result['has_active_recipes'] == true) {

        var newpara = $('<p></p>').text('This Lab Controller has active recipes, do you want to delete?')
        var dialog_div = $('<div></div>').attr('title','Delete').append(newpara)

        dialog_div.dialog({
            resizable: false,
            height:200,
            modal: true,
            buttons: {
                "Delete": function() {
                    $( this ).dialog( "close" );
                    window.location.replace('./remove?id=' + lc_id)
                },
                Cancel: function() {
                    $( this ).dialog( "close" );
                }
            }
        });

    } else {
        window.location.replace('./remove?id=' + lc_id)
    }
}

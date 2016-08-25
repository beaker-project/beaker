AckPanel = function() {
}

AckPanel.prototype.initialize = function () {
    
     bindMethods(this)  
}
AckPanel.prototype.response_loading_prefix = 'ack_response_loading_'

AckPanel.prototype.update = function (rs_id,response_id) { 
    var params = { 'tg_format' : 'json',
                   'tg_random' : new Date().getTime(),
                   'response_id' : response_id,
                   'recipe_set_id' : rs_id }

    AjaxLoader.prototype.add_loader('response_' + rs_id)
    var d = loadJSONDoc('./update_recipe_set_response?' + queryString(params)) 
    d.addCallback(this.update_results)
}

AckPanel.prototype.update_results = function (result) { 
    var rs_id =  result['rs_id']
    AjaxLoader.prototype.remove_loader('response_' + rs_id)
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
            text = 'Error udpating response'
        }
        colour = '#FF0000'
        response_type = 'failure'
    }
   

    if ($("span[id^='response_"+rs_id+"_']").length) { 
        return_msg = $("span[id^='response_"+rs_id+"_']").text(text)
        return_msg.fadeIn(1000)
        return_msg.fadeOut(1000)

    } else {
        var return_msg = $("<span></span>").html(text).css('background-color',colour).css('display','inline-block').css('margin','1em 0 0 2em').attr('id','response_'+rs_id+'_'+response_type).addClass('rounded-side-pad')
        $('#response_'+rs_id).after(return_msg).fadeIn("slow")
        return_msg.fadeOut(1000)
    }
    //window.setTimeout(function () { return_msg.detach() },1100);
}

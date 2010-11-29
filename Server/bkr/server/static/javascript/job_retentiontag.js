
$(document).ready(function() { last_good_retentiontag = $('#job_retentiontag').val()})
var last_good_retentiontag = null
function job_retentiontag_save_success() {

    var msg = $('<div class="msg success" style="max-width: 20em;">Tag has been updated</div>')
                .hide()
                .appendTo($('#job_retentiontag').parent()) 
                .fadeIn(1000)
                .oneTime(2000, 'hide', function () { $(this).fadeOut(1000).remove(); });
    last_good_retentiontag = $('#job_retentiontag').val()
}

function job_retentiontag_before() {
                AjaxLoader.prototype.add_loader('job_retentiontag')
}


function job_retentiontag_complete() {
                AjaxLoader.prototype.remove_loader('job_retentiontag') 
}


function job_retentiontag_save_failure(fail_msg) {

                var msg = $('<div class="msg warn" style="max-width: 20em;">Unable to update Tag</div>')
                        .hide()
                        .appendTo($('#job_retentiontag').parent())
                        .fadeIn(1000)
                        .oneTime(2000, 'hide', function () { $(this).fadeOut(1000).remove(); });
                 $('#job_retentiontag').val(last_good_retentiontag)
}

function job_retentiontag_get_data(existing_data) {

    params = existing_data
    if (params['retentiontag'] == undefined) {
        params['retentiontag'] = $('#job_retentiontag').val()
    }
    params['tg_random'] = new Date().getTime()
    return params
}

function RetentionTagChange(action, data, options) {
    data = job_retentiontag_get_data(data)
    if (options['before']) {
        eval(options['before']);
    }

    var d = loadJSONDoc(action + "?" + queryString(data))

    var determinator = function(options, result) {
        if (result['success'] == true) {
            do_complete(options,true)
        } else {
            if (result['vars']['NEEDS_PRODUCT']) {
                pop_up_product_choice(data,action,options,result['vars'])
                eval(options['on_complete'])
            } else if (result['vars']['NEEDS_NO_PRODUCT']) {
                pop_up_no_product_choice(data,action,options)
                eval(options['on_complete'])
            } else {
                do_complete(options,fail)
            }
        }
    }
    d.addCallback(determinator,options)
}

function pop_up_no_product_choice(data,action,options)　{
    var newspan = $('<p></p>').text('This tag is not compatible with '+
        'having a product, would you like to clear your product?')
    dialog_div = $('<div></div>').attr('title','Clear Product').append(newspan)
 
    dialog_div.dialog({
        open:function() {
            $(this).parents(".ui-dialog:first").find(".ui-dialog-titlebar-close").remove();
        },
        resizable: false,
        width: 500,
        height: 200,
        modal: true,
        buttons : { "Clear product" : function() {$('#job_product').val(0); 
                                                  data['product'] = 0;
                                                  $(this).dialog("close"); 
                                                  RetentionTagChange(action,data,options); },
                   "Cancel" : function() { $(this).dialog('close');do_complete(options,false)}}
    });
}

function pop_up_product_choice(data,action,options, vars)　{
    var newspan = $('<p></p>').text('This tag requires a product, please choose one')
    var product_clone = $('#job_product').clone()
    product_clone.attr('id', 'job_product_clone')
    invalid_products = vars['INVALID_PRODUCTS']
    for (i in invalid_products) {
        product_clone.find("option[value='" + invalid_products[i] + "']").remove()
    }
    product_clone.attr('onchange','')
    dialog_div = $('<div></div>').attr('title','Select Product').append(newspan).append(product_clone)
    dialog_div.dialog({
        open:function() {
            $(this).parents(".ui-dialog:first").find(".ui-dialog-titlebar-close").remove();
        },
        resizable: false,
        height: 200,
        width:800,
        modal: true,
        buttons : { "Select" : function() { product_selector(action,data,options);        $(this).dialog("close"); },
                    "Cancel" : function() {$(this).dialog("close");do_complete(options,false)}}

    });
}

function do_complete(options,success) {
  if (success) {
    eval(options['on_success'])
  } else {
    eval(options['on_failure'])
  }
  eval(options['on_complete'])
}

function product_selector(action,data,options) {

        $('#job_product').val($('#job_product_clone').val());
        data['product'] = $('#job_product').val();
        RetentionTagChange(action,data,options);

}

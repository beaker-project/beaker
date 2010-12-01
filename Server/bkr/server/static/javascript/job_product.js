$(document).ready(function() { last_good_product = $('#job_product option:selected').val()})

function ProductChange(action, data, options) {
    data = job_product_get_data(data)
    if (options['before']) {
        eval(options['before']);
    }

    var d = loadJSONDoc(action + "?" + queryString(data))

    var determinator = function(options, result) {
        if (result['success'] == true) {
            do_complete(options,true)
        } else {
            if (result['vars']['NEEDS_TAG']) {
                pop_up_tag_choice(action,data,options,result['vars'])
                eval(options['on_complete'])
            } else {
                do_complete(options,false)
            }
        }
    }

    d.addCallback(determinator,options)
}

function do_complete(options,success) {
  if (success) {
    eval(options['on_success'])
  } else {
    eval(options['on_failure'])
  }

  eval(options['on_complete'])
}

function pop_up_tag_choice(action,data,options,vars)　{
    var tags = $('#job_retentiontag')
    var new_span = $("<p></p>").text('This product requires that you select one of the following tags:')

    var select_tags = $("<select id='valid_tags'></select>")
    only_valid_tags = vars['VALID_TAGS']
    for (i in only_valid_tags) {
        tag_info = only_valid_tags[i]
        id = tag_info[0]
        _val = tag_info[1]
        new_option = $('<option></option>').val(id)
        new_option.text(_val)
        select_tags.append(new_option)
    }

    dialog_div = $('<div></div>').attr('title','Change Tag').append(new_span).append(select_tags)
    dialog_div.dialog({
            open:function() {
                $(this).parents(".ui-dialog:first").find(".ui-dialog-titlebar-close").remove();
            },
            resizable: false,
            height: 300,
            width:400,
            modal: true,
            buttons : { "Save product" : function() {

                                                    $('#job_retentiontag').val($('#valid_tags option:selected').val());
                                                    data['retentiontag'] = $('#valid_tags option:selected').val()
                                                    data['product'] = $('#job_product option:selected').val()
                                                    $(this).dialog("close");
                                                    $('#valid_tags').remove()
                                                    ProductChange(action,data,options);

                                                    },

                        "Cancel" : function() { $(this).dialog("close");do_complete(options,false)}} 
    });
}

function retention_tag_selector(action,data,options) {
    $('#job_retentiontag').val($('#valid_tags option:selected').val());
    data['retentiontag'] = $('#valid_tags option:selected').val()
    data['product'] = $('#job_product option:selected').val()
    ProductChange(action,data,options);
}

function job_product_save_success() {
    var msg = $('<div class="msg success" style="max-width: 20em;">Product has been updated</div>')
                .hide()
                .appendTo($('#job_product').parent()) 
                .fadeIn(1000)
                .oneTime(2000, 'hide', function () { $(this).fadeOut(1000).remove(); });
    last_good_product = $('#job_product option:selected').val()
}

function job_product_before() {
                AjaxLoader.prototype.add_loader('job_product')
}


function job_product_complete() {
                AjaxLoader.prototype.remove_loader('job_product') 
}


function job_product_save_failure() {
                var msg = $('<div class="msg warn" style="max-width: 20em;">Unable to update product</div>')
                        .hide()
                        .appendTo($('#job_product').parent())
                        .fadeIn(1000)
                        .oneTime(2000, 'hide', function () { $(this).fadeOut(1000).remove(); });
                 $('#job_product').val(last_good_product)
            }

function job_product_get_data(existing_data) {

    params = existing_data
    if (params['product'] == undefined) {
        params['product'] = $('#job_product').val()
    }
    params['tg_random'] = new Date().getTime()
    return params
}

JobMatrix = function (jobs,whiteboard,filter) {

    this.job_field = jobs
    this.whiteboard_field = whiteboard
    this.filter_field = filter

    this.job_value = null
    this.whiteboard_value = null
    this.filter_value = null 
    bindMethods(this)
}


JobMatrix.prototype.initialize = function() {
    bindMethods(this)
}


JobMatrix.prototype.submit_changes = function() {
  if (getNodeAttribute(this.whiteboard_field,'readonly') != null) {
      getElement(this.whiteboard_field).setAttribute('disabled',1) 
  }


  if (getNodeAttribute(this.job_field,'readonly') != null) {
      getElement(this.job_field).setAttribute('disabled',1) 
  }
}

JobMatrix.prototype.clicked_whiteboard = function() {
    getElement(this.whiteboard_field).removeAttribute('readonly')
    getElement(this.job_field).setAttribute('readonly',1) 
}


JobMatrix.prototype.clicked_jobs = function() {
    getElement(this.job_field).removeAttribute('readonly')
    getElement(this.whiteboard_field).setAttribute('readonly',1)    
}

JobMatrix.prototype.filter_on_whiteboard = function(event) {
    var params = { 'tg_format' : 'json',
                   'tg_random' : new Date().getTime(),
                   'filter' : getElement(this.filter_field).value }
    var d = loadJSONDoc('./get_whiteboard_options_json?' + queryString(params))
    removeElementClass('loading','hidden')
    d.addCallback(this.replace_whiteboard)
} 


JobMatrix.prototype.show_comment = function (result) { 
    rs_id = result.rs_id
    comment = result.comment
    
    newspan = SPAN({'id':'comment_remote_form_nack_text_' + rs_id,'class':'hidden','title' : 'Nack comment for RS# '+rs_id },comment)
    appendChildNodes('comment_remote_form_nacks_' +rs_id,newspan) 
    $('#comment_remote_form_nack_text_1').dialog({height:140,
                                                  modal:true,
                                                  buttons: { 
                                                    'Edit' : function() {
                                                               var t_box = $("<textarea></textarea>").
                                                                           html($('#comment_remote_form_nack_text_1').
                                                                           text()).
                                                                           attr('id','comment_textbox_1').
                                                                           addClass('hidden'); 
                                                               $('#comment_remote_form_nacks_1').after(t_box);
                                                            }
                                                        }
    
                                                })
}

JobMatrix.prototype.replace_whiteboard = function(result) { 
    replaceChildNodes(this.whiteboard_field, map(this.replaceOptions, result.options));
    addElementClass('loading','hidden') 
}

JobMatrix.prototype.replaceOptions = function(arg) {
    option = OPTION({"value": arg[0]}, arg[0])
    return option
}


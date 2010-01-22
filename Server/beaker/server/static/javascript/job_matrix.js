connect(document,'onsubmit', submit_changes)

function submit_changes() {
  if (getNodeAttribute('remote_form_whiteboard','readonly') != null) {
      getElement('remote_form_whiteboard').setAttribute('disabled',1) 
  }


  if (getNodeAttribute('remote_form_job_ids','readonly') != null) {
      getElement('remote_form_job_ids').setAttribute('disabled',1) 
  }
}

function clicked_whiteboard() {
    getElement('remote_form_whiteboard').removeAttribute('readonly')
    getElement('remote_form_job_ids').setAttribute('readonly',1) 
}


function clicked_jobs() {
    getElement('remote_form_job_ids').removeAttribute('readonly')
    getElement('remote_form_whiteboard').setAttribute('readonly',1)    
}


function filter_on_whiteboard(event) {
    var params = { 'tg_format' : 'json',
                   'tg_random' : new Date().getTime(),
                   'filter' : getElement('remote_form_whiteboard_filter').value }
    var d = loadJSONDoc('./get_whiteboard_options_json?' + queryString(params))
    d.addCallback(replace_whiteboard)
} 


function replace_whiteboard(result) { 
    replaceChildNodes('remote_form_whiteboard', map(replaceOptions, result.options));
}

function replaceOptions(arg) {
    option = OPTION({"value": arg}, arg)
    return option
}

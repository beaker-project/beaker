<div xmlns:py="http://purl.org/kid/ns#">
<script type='text/javascript'>
var matrix = new JobMatrix("${job_ids.field_id}","${whiteboard.field_id}","${whiteboard_filter.field_id}")
connect(document,'onsubmit', matrix.submit_changes);

function compareArray(a,b) {
    if (a.length != b.length) return false;
        for (var i = 0; i &lt; b.length; i++) {
                if (a[i] != b[i]) return false;
        }
        return true;
}

$(document).ready( function() {
    current_job_ids = $('#remote_form_job_ids').val().split(" ")

    $('#${whiteboard_filter_button.field_id}').click(function () { matrix.filter_on_whiteboard()  } )
    $('#${whiteboard.field_id}').click(function () { 
        matrix.clicked_whiteboard() 
    } )

    $('#${job_ids.field_id}').click(function () { 
        matrix.clicked_jobs() 
    } )

})



</script>
<div class="job-matrix">
<form action='${tg.url(action)}' name="${name}">   
     <div class="whiteboard-selector">
    
         <h3 style="display:inline"> ${whiteboard.label}</h3><br />
         <div onclick="javascript:matrix.clicked_whiteboard()" py:content="whiteboard.display(options=whiteboard_options)" />

         <strong class='smallfont'>${whiteboard_filter.label}</strong>
         <span style='display:inline'  py:content='whiteboard_filter.display()' />
         <span style='display:inline' py:content="whiteboard_filter_button.display(options={'label' : 'Filter'})" />
         <span id='loading' class='hidden'>&nbsp;&nbsp;&nbsp;&nbsp;</span>
    </div>
      
    <div style="float:left;padding-bottom:3em;">
        <h3 style="display:inline">${job_ids.label}</h3><br />
        <div onclick="javascript:matrix.clicked_jobs()" py:content="job_ids.display(value=job_ids_vals)" />
    </div>
        <br style="clear:both" />
       <button class='btn' type='submit'>Generate</button>
        <div style="clear:left" id="nacks">
        <h5 style="display:inline">${nack_list.label}</h5>
            <input py:if="toggle_nacks_on" id="toggle_nacks_on" name="toggle_nacks_on" type="checkbox" checked="" />
            <input py:if="not toggle_nacks_on" id="toggle_nacks_on" name="toggle_nacks_on" type="checkbox" />
        </div>
    <div id='matrix-report' py:if="grid">
      ${grid.display(list)}
    </div>
</form>
</div>
</div>



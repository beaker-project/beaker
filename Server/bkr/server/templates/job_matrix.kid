<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
<body>
<head>
<script type="text/javascript" src="${tg.url('/static/javascript/jquery.cookie.js')}"></script>
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
    
    $("span[id ^='comment_remote_form_nacks']").click(
                function() { 
                          matrix.get_nack_comment(1); //this is just testing!!!!!!!11
                          
                        
        }) 


    $("form[name='remote_form']").submit(function() {
        if ($('#${job_ids.field_id}').attr('readonly') == true) { //seems we are searching by whiteboard, don't change any nacks
             $('#toggle_nacks_on').remove() 
             exit;        
        }

        jobs_ids_now =  $('#remote_form_job_ids').val().split(" ")
        same = compareArray(jobs_ids_now,current_job_ids)

        if (!same) {  //if we have changed our job ids, we will not be changing any nacks
            $('#toggle_nacks_on').remove() 
        }

    })

    if ($.cookie('nacks_field')) {
        switch ($.cookie('nacks_field'))
        {
            case 'hide': 
                $('#nacks').css('display','none')
            break;
            case 'show':
                $('#nacks').css('display','block')
            break;
        }
    }

    $('#${whiteboard_filter.field_id}').blur(function () { matrix.filter_on_whiteboard()  } )
    $('#${whiteboard.field_id}').click(function () { 
        matrix.clicked_whiteboard() 
    } )

    $('#${job_ids.field_id}').click(function () { 
        matrix.clicked_jobs() 
    } )
    
    $('#toggle_nacks').click(function () { 
                $('#nacks').toggle()   
                if ($('#nacks').css('display') == 'none') {
                        $.cookie('nacks_field','hide')    
                    } else {
                        $.cookie('nacks_field','show')    
                        } 
                    } )

})



</script>
</head>
<div style='padding-left:2em'>
<form action='${action}' name="${name}">   
     <div style='float:left'> 
    
         <h3 style="display:inline"> ${whiteboard.label}</h3><br />
         <div class='margined' onclick="javascript:JobMatrix.clicked_whiteboard()" py:content="whiteboard.display(options=whiteboard_options)" />   

         <strong class='smallfont'>${whiteboard_filter.label}</strong>
         <span style='display:inline'  py:content='whiteboard_filter.display()' />
         <span id='loading' class='hidden'>&nbsp;&nbsp;&nbsp;&nbsp;</span>
    </div>
      
    <div style="float:left">
        <h3 style="display:inline">${job_ids.label}</h3><br />
        <div class="margined" onclick="javascript:clicked_jobs()" py:content="job_ids.display(value=job_ids_vals)" /> 
    </div>


        <div style="clear:left"  class="margined" py:if="toggle_nacks" id="nacks">
        <h3 style="display:inline">${nack_list.label}</h3><br />
        <div clas="margined" py:content="nack_list.display(options=nacks, list_attrs={'class' : 'checkboxlist nacks'})" />
            <input id="toggle_nacks_on" name="toggle_nacks_on" type="hidden" value="1" /> 
        </div>
 
      <br style="clear:both" /> 
        <a py:if="toggle_nacks" id="toggle_nacks" style="font-size:x-small" href="#">Toggle Nacks </a>
      <input class='submit-button' type='submit' value='Generate' />
  
    <div py:if="grid"> 
      ${grid.display(list)} 
    </div>
</form>
</div>
</body>
</html>




<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
<body>
<head>
<script type='text/javascript'>
$(document).ready( function() {
    $('#remote_form_whiteboard_filter').blur(function () { filter_on_whiteboard()  } )
})

</script>
</head>
<div style='padding-left:2em'>
<form action='${action}' name="${name}">  

     <div style='float:left'> 
         <h3 style="display:inline"> ${whiteboard.label}</h3><br />
         <div class='margined' onclick="javascript:clicked_whiteboard()" py:content="whiteboard.display(options=whiteboard_options)" />   

         <strong class='smallfont'>${whiteboard_filter.label}</strong>
         <span style='display:inline'  py:content='whiteboard_filter.display()' />

     </div>
   
     <div> 
        <h3 style="display:inline">${job_ids.label}</h3><br />
        <div class='margined'  onclick="javascript:clicked_jobs()" py:content="job_ids.display(value=job_ids_vals)" /> 
     </div>
   
      <br /> 
      <input class='submit-button' type='submit' value='Generate' />
  
    <div py:if="grid"> 
      ${grid.display(list)} 
    </div>
</form>
</div>
</body>
</html>




<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
<body>
<div style='padding-left:2em'>
<form action='${action}' name="${name}">  

     <div style='float:left;padding-right:5em'> 
         <h3 style="display:inline"> ${whiteboard.label}</h3><br />
         <div onclick="javascript:clicked_whiteboard()" py:content="whiteboard.display(options=whiteboard_options)" />   

         <strong class='smallfont'>${whiteboard_filter.label}</strong>
         <span style='display:inline'  py:content='whiteboard_filter.display()' />
     </div>
   
     <div> 
        <h3 style="display:inline">${job_ids.label}</h3><br />
        <div onclick="javascript:clicked_jobs()" py:content="job_ids.display()" /> 
     </div>

    <input type='submit' value='Generate' />  
    <div py:if="grid"> 
      testing here
      ${grid.display(list)} 
    </div>
</form>
</div>
</body>
</html>




<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
<body>
<div>
<form action='${action}' name="${name}">  
     <span>
      <h3>${whiteboard.label}</h3>
      <div py:content="whiteboard.display(**params_for(whiteboard))" />
      <strong class='smallfont'>${whiteboard_filter.label}</strong>
      <span py:content='whiteboard_filter.display()' />
    </span>
    <span>
      <h3>${job_ids.label}</h3>
      <span py:content="job_ids.display(**params_for(job_ids))" />
    </span>
    
    <div>
      <input type='submit' value='${submit_text}' />
    </div>
</form>
</div>
</body>
</html>




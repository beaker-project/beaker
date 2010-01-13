<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
<body>
<div>
 
    <span>
      <h3>${whiteboard.label}</h3>
      <div py:content="whiteboard.display(**params_for(whiteboard))" />
      <strong class='smallfont'>${whiteboard_filter.label}</strong>
      <span py:content='whiteboard_filter.display()' />
    </span>

    <span>
      <h3>${projects.label}</h3>
      <div py:content="projects.display(**params_for(projects))" />
      <strong class='smallfont'>${projects_filter.label}</strong>
      <span py:content="projects_filter.display()" />
      
    </span>

    <span>
      <h3>${job_ids.label}</h3>
      <span py:content="job_ids.display(**params_for(job_ids))" />
    </span>
    
    <div>
      <span py:content='generate_button.display()'/>
    </div>
</div>
</body>
</html>




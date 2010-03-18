<div xmlns:py="http://purl.org/kid/ns#">
 <?python
    if recipe.result:
        result = recipe.result.result == 'Pass' and 'pass' or 'fail'
    else:
        result = 'fail'
 ?>

 <table class="show ${result}">
  <tr>
   <td class="title"><b>Recipe ID</b></td>
   <td class="value"><a class="list" href="${tg.url('/recipes/%s' % recipe.id)}">${recipe.t_id}</a></td>
   <td class="title"><b>Status</b></td>
   <td class="value">${recipe.status}</td>
   <td class="title"><b>Result</b></td>
   <td class="value">${recipe.result}</td>
  </tr>
  <tr>
   <td class="title"><b>Distro</b></td>
   <td class="value">${recipe.distro.link}</td>
   <td class="title"><b>Arch</b></td>
   <td class="value">${recipe.arch}</td>
   <td class="title"><b>Family</b></td>
   <td class="value">${recipe.distro.osversion}</td>
  </tr>
  <tr>
   <td class="title"><b>Queued</b></td>
   <td class="value">${recipe.recipeset.queue_time}</td>
   <td class="title"><b>Started</b></td>
   <td class="value">${recipe.start_time}</td>
   <td class="title"><b>Action(s)</b></td>
   <td class="value">${recipe.action_link}</td>
  </tr>
  <tr>
   <td class="title"><b>Finsihed</b></td>
   <td class="value">${recipe.finish_time}</td>
   <td class="title"><b>Duration</b></td>
   <td class="value">${recipe.duration}</td>
  </tr>
  <tr py:if="recipe.system">
   <td class="title"><b>System</b></td>
   <td class="value">${recipe.system.link}</td>
   <td class="title"><b>Progress</b></td>
   <td class="value">${recipe.progress_bar}</td>
  </tr>
  <tr>
   <td class="title"><b>Whiteboard</b></td>
   <td class="value" colspan="6">${recipe.whiteboard}</td>
  </tr>
  <tr>
   <td class="title"><b>Logs</b></td>
   <td class="value logs"><br py:for="log in recipe.logs">${log.link}</br></td>
  </tr>
  <tr py:if="recipe.systems">
   <td class="title"><b>Possible Systems</b></td>
   <td class="value">${len(recipe.systems)}</td>
   <td class="title"><b>Max Wait Time</b></td>
   <td class="value" colspan="6">Not Implemented yet..</td>
  </tr>
 </table>

 <div py:if="recipe_tasks_widget" class="recipe-tasks ${result}">
  <h2>Task Runs</h2>
  <p py:content="recipe_tasks_widget(tasks=recipe.all_tasks)">Recipe Tasks goes here</p>
 </div>
</div>

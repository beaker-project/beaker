<table xmlns:py="http://purl.org/kid/ns#" 
       width="97%" 
       class="list" 
       py:if="recipe_tasks">
 <tr class="list">
  <th class="list">ID</th>
  <th class="list">Name</th>
  <th class="list">Start</th>
  <th class="list">Finish</th>
  <th class="list">Duration</th>
  <th class="list">Status</th>
  <th class="list">Result</th>
  <th class="list">Logs</th>
 </tr>
 <tr class="list" py:for="recipe_task in recipe_tasks">
   <td class="list">${recipe_task.t_id}</td>
   <td class="list">${recipe_task.path}</td>
   <td class="list">${recipe_task.start_time}</td>
   <td class="list">${recipe_task.finish_time}</td>
   <td class="list">${recipe_task.duration}</td>
   <td class="list">${recipe_task.status}</td>
   <td class="list">${recipe_task.result}</td>
   <td class="list">&nbsp;</td>
 </tr>
</table>

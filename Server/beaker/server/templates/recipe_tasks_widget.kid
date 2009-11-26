<table xmlns:py="http://purl.org/kid/ns#" 
       width="97%" 
       class="list" 
       py:if="recipe_tasks">
 <tr class="list">
  <th class="list">Name</th>
  <th class="list">Start</th>
  <th class="list">Finish</th>
  <th class="list">Duration</th>
  <th class="list">Status</th>
  <th class="list">Result</th>
 </tr>
 <tr py:for="i, recipe_task in enumerate(recipe_tasks)" class="${i%2 and 'odd' or 'even'}">
   <!-- Depending on if its a RecipeTask or a RecipeTaskResult we 
        display a different row 
   -->
   <?python
       if recipe_task.result:
           result = recipe_task.result.result == 'Pass' and 'pass' or 'fail'
       else:
           result = 'fail'
   ?>
   <td py:if="recipe_task.is_task()" class="list ${result}">${recipe_task.link}</td>
   <td py:if="not recipe_task.is_task()" class="list ${result}">&nbsp;&nbsp;${recipe_task.short_path}</td>
   <td class="list ${result}">${recipe_task.start_time}</td>
   <td class="list ${result}">${recipe_task.finish_time}</td>
   <td class="list ${result}">${recipe_task.duration}</td>
   <td class="list ${result}">${recipe_task.status}</td>
   <td class="list ${result}">${recipe_task.result}</td>
 </tr>
</table>

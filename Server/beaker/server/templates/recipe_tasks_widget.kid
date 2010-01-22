<table xmlns:py="http://purl.org/kid/ns#" 
       width="97%" 
       class="list" 
       py:if="recipe_tasks">
 <tr class="list">
  <th class="list">Name</th>
  <th class="list">Logs</th>
  <th class="list">Start</th>
  <th class="list">Finish</th>
  <th class="list">Duration</th>
  <th class="list">Status</th>
  <th class="list">Result</th>
  <th class="list">Score</th>
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
   <span py:if="recipe_task.is_task()">
   <td class="list ${result}">${recipe_task.link}</td>
   <td class="list ${result}"><br py:for="log in recipe_task.logs">${log.link}</br></td>
   <td class="list ${result}">${recipe_task.start_time}</td>
   <td class="list ${result}">${recipe_task.finish_time}</td>
   <td class="list ${result}">${recipe_task.duration}</td>
   <td class="list ${result}">${recipe_task.status}</td>
   <td class="list ${result}">${recipe_task.result}</td>
   <td class="list ${result}">&nbsp;</td>
   </span>
   <span py:if="recipe_task.is_result()">
   <td class="list ${result}">&nbsp;&nbsp;${recipe_task.short_path}</td>
   <td class="list ${result}"><br py:for="log in recipe_task.logs">${log.link}</br></td>
   <td class="list ${result}">${recipe_task.start_time}</td>
   <td class="list ${result}">&nbsp;</td>
   <td class="list ${result}">&nbsp;</td>
   <td class="list ${result}">&nbsp;</td>
   <td class="list ${result}">${recipe_task.result}</td>
   <td class="list ${result}">${recipe_task.score}</td>
   </span>
 </tr>
</table>

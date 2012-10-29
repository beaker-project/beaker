<div xmlns:py="http://purl.org/kid/ns#">
 <?python
  from bkr.server.model import RecipeTask, RecipeTaskResult
  from urlparse import urlparse
  from cgi import  parse_qs
  if getattr(tg, 'paginate', False):
      if tg.paginate.href_first:
          data_first = parse_qs(urlparse(tg.paginate.href_first)[4])
      if tg.paginate.href_prev:
          data_prev = parse_qs(urlparse(tg.paginate.href_prev)[4])
      if tg.paginate.href_next:
          data_next = parse_qs(urlparse(tg.paginate.href_next)[4])
      if tg.paginate.href_last: 
          data_last = parse_qs(urlparse(tg.paginate.href_last)[4])
 ?>
 <table width="97%">
  <tr py:if="getattr(tg, 'paginate', False) and tg.paginate.page_count > 2">
   <td align="center">
    <span py:if="tg.paginate.href_prev">${link.display("&lt;&lt;", action=tg.url(action), data=data_first, update="task_items")}</span>
    <span py:if="tg.paginate.href_prev">${link.display("&lt;", action=tg.url(action), data=data_prev, update="task_items")}</span>&#160;
    <span py:if="tg.paginate.href_next">${link.display("&gt;", action=tg.url(action), data=data_next, update="task_items")}</span>
    <span py:if="tg.paginate.href_next">${link.display("&gt;&gt;", action=tg.url(action), data=data_last, update="task_items")}</span>
   </td>
  </tr>
 </table>
 <table width="97%" 
        class="list" 
        py:if="tasks">
  <tr class="list">
   <th class="list" py:if="not hidden.has_key('rid')">Run ID</th>
   <th class="list" py:if="not hidden.has_key('task')">Task</th>
   <th class="list" py:if="hidden.has_key('task')">&nbsp;</th>
   <th class="list" py:if="not hidden.has_key('distro_tree')">Distro Tree</th>
   <th class="list" py:if="not hidden.has_key('system')">System</th>
   <th class="list" py:if="not hidden.has_key('start')"><br>StartTime</br><br>[FinishTime]</br><br>[Duration]</br></th>
   <th class="list" py:if="not hidden.has_key('logs')">Logs</th>
   <th class="list" py:if="not hidden.has_key('status')">Status</th>
   <th class="list" py:if="not hidden.has_key('result')">Result</th>
   <th class="list" py:if="not hidden.has_key('score')">Score</th>
  </tr>
  <span py:for="i, task in enumerate(tasks)" py:strip="1">
    <!-- Depending on if its a RecipeTask or a RecipeTaskResult we 
         display a different row 
    -->
    <span py:if="isinstance(task, RecipeTask)" py:strip="1">
    <?python
        result = task.is_failed() and 'fail' or 'pass'
    ?>
   <tr class="${i%2 and 'odd' or 'even'} ${result}_recipe_${task.recipe.id} recipe_${task.recipe.id}">
    <td class="list task" py:if="not hidden.has_key('rid')">
     <a name="task${task.id}">${task.link_id}</a>
    </td>
    <td class="list task" py:if="not hidden.has_key('task')">
     ${task.link}
    </td>
    <td class="list task" py:if="hidden.has_key('task')">&nbsp;</td>
    <td class="list task" py:if="not hidden.has_key('distro_tree')">
     ${task.recipe.distro_tree == None and ' ' or task.recipe.distro_tree.link}
    </td>
    <td class="list task" py:if="not hidden.has_key('system')">
     ${task.recipe.resource == None and ' ' or task.recipe.resource.link}
    </td>
    <td class="list task" style="white-space:nowrap;" py:if="not hidden.has_key('start')">
      <span class="datetime">${task.start_time}</span><br/>
      <span class="datetime">${task.finish_time}</span><br/>
      ${task.duration}
    </td>
    <td class="list task" py:if="not hidden.has_key('logs')">
     <br py:for="log in task.logs">${log.link}</br>
    </td>
    <td class="list task" py:if="not hidden.has_key('status')">
     ${task.status}
    </td>
    <td class="list task" py:if="not hidden.has_key('result')">
     ${task.result}
    </td>
    <td class="list task" py:if="not hidden.has_key('score')">
     &nbsp;
    </td>
    </tr>
    <span py:for="task_result in task.results" py:strip="1">
    <?python
        result = task.is_failed() and 'fail' or 'pass'
    ?>
     <tr class="${i%2 and 'odd' or 'even'} ${result}_recipe_${task.recipe.id} recipe_${task.recipe.id}">
    <td class="list result" py:if="not hidden.has_key('rid')">
     &nbsp;
    </td>
    <td class="list result">
     &nbsp;&nbsp;${task_result.short_path}
    </td>
    <td class="list result" py:if="not hidden.has_key('distro_tree')">
     &nbsp;
    </td>
    <td class="list result" py:if="not hidden.has_key('system')">
     &nbsp;
    </td>
    <td class="list task" style="white-space:nowrap;" py:if="not hidden.has_key('start')">
      <span class="datetime">${task_result.start_time}</span>
    </td>
    <td class="list result" py:if="not hidden.has_key('logs')">
     <br py:for="log in task_result.logs">${log.link}</br>
    </td>
    <td class="list result" py:if="not hidden.has_key('status')">
     &nbsp;
    </td>
    <td class="list result" py:if="not hidden.has_key('result')">
     ${task_result.result}
    </td>
    <td class="list result" py:if="not hidden.has_key('score')">
     ${task_result.score}
    </td>
    </tr>
    </span>
   </span>
  </span>
 </table>
</div>

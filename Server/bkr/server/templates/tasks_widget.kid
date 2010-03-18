<div xmlns:py="http://purl.org/kid/ns#">
 <?python
  from bkr.server.model import RecipeTask, RecipeTaskResult
  from urlparse import urlparse
  from cgi import  parse_qs
  if getattr(tg, 'paginate', False):
      if tg.paginate.href_first:
          action_first = urlparse(tg.paginate.href_first)[2]
          data_first = parse_qs(urlparse(tg.paginate.href_first)[4])
      if tg.paginate.href_prev:
          action_prev = urlparse(tg.paginate.href_prev)[2]
          data_prev = parse_qs(urlparse(tg.paginate.href_prev)[4])
      if tg.paginate.href_next:
          action_next = urlparse(tg.paginate.href_next)[2]
          data_next = parse_qs(urlparse(tg.paginate.href_next)[4])
      if tg.paginate.href_last:
          action_last = urlparse(tg.paginate.href_last)[2]
          data_last = parse_qs(urlparse(tg.paginate.href_last)[4])
 ?>
 <table width="97%">
  <tr py:if="getattr(tg, 'paginate', False) and tg.paginate.page_count > 2">
   <td align="center">
    <span py:if="tg.paginate.href_prev">${link.display("&lt;&lt;", action=action_first, data=data_first, update="task_items")}</span>
    <span py:if="tg.paginate.href_prev">${link.display("&lt;", action=action_prev, data=data_prev, update="task_items")}</span>&#160;
    <span py:if="tg.paginate.href_next">${link.display("&gt;", action=action_next, data=data_next, update="task_items")}</span>
    <span py:if="tg.paginate.href_next">${link.display("&gt;&gt;", action=action_last, data=data_last, update="task_items")}</span>
   </td>
  </tr>
 </table>
 <table width="97%" 
        class="list" 
        py:if="tasks">
  <tr class="list">
   <th class="list" py:if="not hidden.has_key('rid')">Run ID</th>
   <th class="list" py:if="not hidden.has_key('task')">Task</th>
   <th class="list" py:if="not hidden.has_key('distro')">Distro</th>
   <th class="list" py:if="not hidden.has_key('osmajor')">Family</th>
   <th class="list" py:if="not hidden.has_key('arch')">Arch</th>
   <th class="list" py:if="not hidden.has_key('system')">System</th>
   <th class="list" py:if="not hidden.has_key('start')">Start</th>
   <th class="list" py:if="not hidden.has_key('finish')">Finish</th>
   <th class="list" py:if="not hidden.has_key('duration')">Duration</th>
   <th class="list" py:if="not hidden.has_key('logs')">Logs</th>
   <th class="list" py:if="not hidden.has_key('status')">Status</th>
   <th class="list" py:if="not hidden.has_key('result')">Result</th>
   <th class="list" py:if="not hidden.has_key('score')">Score</th>
  </tr>
  <tr py:for="i, task in enumerate(tasks)" class="${i%2 and 'odd' or 'even'}">
    <!-- Depending on if its a RecipeTask or a RecipeTaskResult we 
         display a different row 
    -->
    <span py:if="isinstance(task, RecipeTask)" py:strip="1">
    <?python
        result = task.is_failed() and 'fail' or 'pass'
    ?>
    <td class="list ${result} task" py:if="not hidden.has_key('rid')">
     <a name="task${task.id}">${task.link_id}</a>
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('task')">
     ${task.link}
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('distro')">
     ${task.recipe.distro == None and ' ' or task.recipe.distro.link}
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('osmajor')">
     ${task.recipe.distro.osversion}
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('arch')">
     ${task.recipe.distro.arch}
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('system')">
     ${task.recipe.system == None and ' ' or task.recipe.system.link}
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('start')">
     ${task.start_time}
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('finish')">
     ${task.finish_time}
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('duration')">
     ${task.duration}
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('logs')">
     <br py:for="log in task.logs">${log.link}</br>
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('status')">
     ${task.status}
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('result')">
     ${task.result}
    </td>
    <td class="list ${result} task" py:if="not hidden.has_key('score')">
     &nbsp;
    </td>
    </span>
    <span py:if="isinstance(task, RecipeTaskResult)" py:strip="1">
    <td class="list ${result} result" py:if="not hidden.has_key('rid')">
     &nbsp;
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('task')">
     &nbsp;&nbsp;${task.short_path}
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('distro')">
     &nbsp;
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('osmajor')">
     &nbsp;
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('arch')">
     &nbsp;
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('system')">
     &nbsp;
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('start')">
     ${task.start_time}
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('finish')">
     &nbsp;
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('duration')">
     &nbsp;
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('logs')">
     <br py:for="log in task.logs">${log.link}</br>
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('status')">
     &nbsp;
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('result')">
     ${task.result}
    </td>
    <td class="list ${result} result" py:if="not hidden.has_key('score')">
     ${task.score}
    </td>
    </span>
  </tr>
 </table>
</div>

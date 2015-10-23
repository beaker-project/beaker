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
  <div class="pagination pagination-right" py:if="tg.paginate.page_count > 2">
    <ul>
      <li py:if="tg.paginate.href_prev">${link.display("&lt;&lt;", action=tg.url(action), data=data_first, update="task_items")}</li>
      <li py:if="tg.paginate.href_prev">${link.display("&lt;", action=tg.url(action), data=data_prev, update="task_items")}</li>
      <li py:if="tg.paginate.href_next">${link.display("&gt;", action=tg.url(action), data=data_next, update="task_items")}</li>
      <li py:if="tg.paginate.href_next">${link.display("&gt;&gt;", action=tg.url(action), data=data_last, update="task_items")}</li>
    </ul>
  </div>
  <table class="table table-condensed table-hover tasks"
        py:if="tasks">
  <thead>
  <tr>
   <th py:if="not hidden.has_key('rid')">Run ID</th>
   <th>Task</th>
   <th py:if="not hidden.has_key('distro_tree')">Distro Tree</th>
   <th py:if="not hidden.has_key('system')">System</th>
   <th py:if="not hidden.has_key('start')"><div>StartTime</div><div>[FinishTime]</div><div>[Duration]</div></th>
   <th py:if="not hidden.has_key('logs')" class="logs">Logs</th>
   <th py:if="not hidden.has_key('status')">Status</th>
   <th py:if="not hidden.has_key('result')">Result</th>
   <th py:if="not hidden.has_key('score')">Score</th>
  </tr>
  </thead>
  <tbody py:for="task in tasks">
    <?python
        result = task.is_failed() and 'fail' or 'pass'
    ?>
   <tr class="${result}_recipe_${task.recipe.id} recipe_${task.recipe.id}" id="task${task.id}">
    <td class="task" py:if="not hidden.has_key('rid')">
     ${task.link_id}
    </td>
    <td class="task">
     ${task.name_markup}
     <span class="version">${task.version}</span>
    </td>
    <td class="task" py:if="not hidden.has_key('distro_tree')">
     ${task.recipe.distro_tree == None and ' ' or task.recipe.distro_tree.link}
    </td>
    <td class="task" py:if="not hidden.has_key('system')">
     ${task.recipe.resource == None and ' ' or task.recipe.resource.link}
    </td>
    <td class="task" style="white-space:nowrap;" py:if="not hidden.has_key('start')">
      <div class="task-start-time datetime" py:if="task.start_time">${task.start_time}</div>
      <div class="task-finish-time datetime" py:if="task.finish_time">${task.finish_time}</div>
      <div class="task-duration">${task.duration}</div>
    </td>
    <td class="task logs" py:if="not hidden.has_key('logs')">
      <ul class="unstyled">
        <li py:for="log in task.logs">${log.link}</li>
      </ul>
    </td>
    <td class="task status${task.status}" py:if="not hidden.has_key('status')">
     ${task.status}
    </td>
    <td class="task result${task.result}" py:if="not hidden.has_key('result')">
     ${task.result}
    </td>
    <td class="task" py:if="not hidden.has_key('score')">
     &nbsp;
    </td>
    </tr>
    <span py:for="task_result in task.results" py:strip="1">
    <?python
        result = task.is_failed() and 'fail' or 'pass'
    ?>
     <tr class="${result}_recipe_${task.recipe.id} recipe_${task.recipe.id}">
    <td class="result" py:if="not hidden.has_key('rid')">
     &nbsp;
    </td>
    <td class="result">
     ${task_result.display_label}
    </td>
    <td class="result" py:if="not hidden.has_key('distro_tree')">
     &nbsp;
    </td>
    <td class="result" py:if="not hidden.has_key('system')">
     &nbsp;
    </td>
    <td class="result" style="white-space:nowrap;" py:if="not hidden.has_key('start')">
      <span class="datetime">${task_result.start_time}</span>
    </td>
    <td class="result logs" py:if="not hidden.has_key('logs')">
      <ul class="unstyled">
        <li py:for="log in task_result.logs">${log.link}</li>
      </ul>
    </td>
    <td class="result" py:if="not hidden.has_key('status')">
     &nbsp;
    </td>
    <td class="result result${task_result.result}" py:if="not hidden.has_key('result')">
     ${task_result.result}
    </td>
    <td class="result" py:if="not hidden.has_key('score')">
     ${task_result.score}
    </td>
    </tr>
    </span>
  </tbody>
 </table>
</div>

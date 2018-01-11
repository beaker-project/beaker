<div xmlns:py="http://purl.org/kid/ns#" id="recipe${recipe.id}">
 <table class="table recipe">
 <tbody>
  <tr>
   <th><span py:strip="True" py:if="hasattr(recipe, 'hostrecipe')">Guest</span> Recipe ID</th>
   <td>${recipe.link}</td>
   <th>Progress</th>
   <td>${recipe.progress_bar}</td>
   <th>Status</th>
   <td>
    <span py:if="recipe.is_dirty" class="statusDirty">Updating…</span>
    <span py:if="not recipe.is_dirty" class="status${recipe.status}">${recipe.status}</span>
    <span py:if="recipe.status == recipe_status_reserved" class="reservation_duration"> (${recipe.time_remaining} remaining)</span>
   </td>
   <th>Result</th>
   <td class="result${recipe.result}">${recipe.result}</td>
  </tr>
  <tr>
   <th>Distro</th>
   <td py:if="recipe.distro_tree is not None">${recipe.distro_tree.link}</td>
   <td><span py:if="recipe.distro_tree is None"> ${recipe.installation.distro_name} ${recipe.installation.variant} ${recipe.installation.arch}</span></td>
   <th>Arch</th>
   <td>${recipe.arch}</td>
   <th>Family</th>
   <td py:if="recipe.distro_tree is not None">${recipe.distro_tree.distro.osversion}</td>
   <td py:if="recipe.distro_tree is None">${recipe.installation.osmajor}</td>
    <?py action_ = action_widget(task=recipe)?>
   <th py:if="action_">Action(s)</th>
   <td py:if="action_">${action_}</td>
  </tr>
  <tr>
   <th>Queued</th>
   <td><span class="datetime">${recipe.recipeset.queue_time}</span></td>
   <th>Started</th>
   <td><span class="datetime">${recipe.start_time}</span></td>
   <th>Finished</th>
   <td><span class="datetime">${recipe.finish_time}</span></td>
   <th>Duration</th>
   <td>${recipe.duration}</td>
  </tr>
  <tr>
   <th>System</th>
   <td colspan="5"><span py:if="recipe.resource" py:strip="True">${recipe.resource.link}</span></td>
   <th>Kickstart</th>
   <td>
    <span py:if="recipe.installation and recipe.installation.rendered_kickstart" py:strip="True">
      <a href="${tg.url('/kickstart/%s' % recipe.installation.rendered_kickstart.id)}">(view)</a>
    </span>
   </td>
  </tr>
  <tr>
   <th>Whiteboard</th>
   <td colspan="7">${recipe.whiteboard}</td>
  </tr>
  <tr>
   <th><button type="button" class="btn" data-toggle="collapse" data-target="#logs_${recipe.id}">Logs</button></th>
   <td colspan="7">
      <ul class="unstyled collapse" id="logs_${recipe.id}">
        <li py:for="log in recipe.logs">${log.link}</li>
      </ul>
    </td>
  </tr>
  <tr py:if="recipe.systems">
   <th>Possible Systems</th>
   <td colspan="7">
     ${recipe_systems}
  </td>
  </tr>
  <tr>
   <td colspan="8">
    <div class="btn-group results-tabs" data-toggle="buttons-radio">
      <a data-toggle="tab" class="btn results-tab" data-cookie-value="all" href="#recipe-${recipe.id}-results">Show Results</a>
      <a data-toggle="tab" class="btn failed-tab" data-cookie-value="fail" href="#recipe-${recipe.id}-failed" py:if="recipe.is_failed()">Show Failed Results</a>
      <a data-toggle="tab" class="btn hide-results-tab" data-cookie-value="" href="#recipe-${recipe.id}-hide">Hide</a>
    </div>
   </td>
  </tr>
 </tbody>
 </table>
<div class="tab-content">
  <div class="tab-pane results-pane" id="recipe-${recipe.id}-results"></div>
  <div class="tab-pane failed-pane" id="recipe-${recipe.id}-failed"></div>
  <div class="tab-pane" id="recipe-${recipe.id}-hide"></div>
</div>
<script type="text/javascript">
$(function () {
    new RecipeTasksOldView({el: $('#recipe${recipe.id}'), recipe_id: ${recipe.id}});
});
</script>
</div>

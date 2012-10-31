<div xmlns:py="http://purl.org/kid/ns#">

<script type="text/javascript">
var STATUS_${recipe.id};

function getresults_${recipe.id}(f)
{

    if (!($('#task_items_${recipe.id}').html()) ) 
    {
        $('#task_all_recipe_${recipe.id}').click()
    } else {
	f()
    }

}

function recipe_callback_${recipe.id}()
{
    switch (STATUS_${recipe.id}) {
	case 'all': 
		showall_${recipe.id}();
    break;
	case 'fail':
		showfail_${recipe.id}();
    break;
    }
}

function showall_${recipe.id}()
{  
    $('.recipe_${recipe.id}').show();
    $('.hide_recipe_${recipe.id}').show();
    $('.fail_show_recipe_${recipe.id}').show();
    $('.all_show_recipe_${recipe.id}').hide();
    $.cookie('recipe_${recipe.id}','all')
}

function showfail_${recipe.id}()
{ 
    $('.recipe_${recipe.id}').hide();
    $('.fail_recipe_${recipe.id}').show();
    $('.hide_recipe_${recipe.id}').show();
    $('.all_show_recipe_${recipe.id}').show();
    $('.fail_show_recipe_${recipe.id}').hide();
    $.cookie('recipe_${recipe.id}','fail')
}

function shownone_${recipe.id}()
{
    $('.recipe_${recipe.id}').hide();
    $('.all_show_recipe_${recipe.id}').show();
    $('.fail_show_recipe_${recipe.id}').show();
    $('.hide_recipe_${recipe.id}').hide();
    $.cookie('recipe_${recipe.id}',null)
}

// I need to set the status here so if we need to call the ajax function,
// the callback knows what we clicked on.
$(document).ready(function() {
    if($.cookie('recipe_${recipe.id}')) 
    {
       switch ($.cookie('recipe_${recipe.id}'))
       {
        case 'all':
	    STATUS_${recipe.id} = 'all';
            getresults_${recipe.id}(showall_${recipe.id});
        break;
        case 'fail':
	    STATUS_${recipe.id} = 'fail';
            getresults_${recipe.id}(showfail_${recipe.id});
        break;
       }
    } else {
        STATUS_${recipe.id} = 'none';
        shownone_${recipe.id}();
    }

    $('#all_recipe_${recipe.id}').click( function() { 
	    STATUS_${recipe.id} = 'all';
     	getresults_${recipe.id}(showall_${recipe.id});
    });
                                                      
                                                    
    $('#failed_recipe_${recipe.id}').click( function() {
        STATUS_${recipe.id} = 'fail';
        getresults_${recipe.id}(showfail_${recipe.id});

      })
    $('#hide_recipe_${recipe.id}').click( function() { shownone_${recipe.id}(); });
    $('#logs_button_${recipe.id}').click(function () { $('#logs_${recipe.id}').toggleClass('hidden', 'addOrRemove'); });

});
</script>

 <table class="show">
  <tr>
   <td class="title"><b>Recipe ID</b></td>
   <td class="value">${recipe.link}</td>
   <td class="title"><b>Progress</b></td>
   <td class="value">${recipe.progress_bar}</td>
   <td class="title"><b>Status</b></td>
   <td class="value">${recipe.status}</td>
   <td class="title"><b>Result</b></td>
   <td class="value">${recipe.result}</td>
  </tr>
  <tr>
   <td class="title"><b>Distro</b></td>
   <td class="value">${recipe.distro_tree.link}</td>
   <td class="title"><b>Arch</b></td>
   <td class="value">${recipe.arch}</td>
   <td class="title"><b>Family</b></td>
   <td class="value">${recipe.distro_tree.distro.osversion}</td>
    <?py action_ = action_widget(task=recipe)?>
   <td py:if="action_" class="title"><b>Action(s)</b></td>
   <td py:if="action_" class="value">${action_}</td>
  </tr>
  <tr>
   <td class="title"><b>Queued</b></td>
   <td class="value"><span class="datetime">${recipe.recipeset.queue_time}</span></td>
   <td class="title"><b>Started</b></td>
   <td class="value"><span class="datetime">${recipe.start_time}</span></td>
   <td class="title"><b>Finished</b></td>
   <td class="value"><span class="datetime">${recipe.finish_time}</span></td>
   <td class="title"><b>Duration</b></td>
   <td class="value">${recipe.duration}</td>
  </tr>
  <tr>
   <td class="title"><b>System</b></td>
   <td class="value"><span py:if="recipe.resource" py:strip="True">${recipe.resource.link}</span></td>
   <td class="title"><b>Kickstart</b></td>
   <td class="value">
    <span py:if="recipe.rendered_kickstart" py:strip="True">
      <a href="${tg.url('/kickstart/%s' % recipe.rendered_kickstart.id)}">(view)</a>
    </span>
   </td>
  </tr>
  <tr>
   <td class="title"><b>Whiteboard</b></td>
   <td class="value" colspan="8" style="white-space: normal;">${recipe.whiteboard}</td>
  </tr>
  <tr>
   <td class="title"><button id="logs_button_${recipe.id}">Logs</button></td>
   <td id="logs_${recipe.id}" class="hidden value" colspan="8"><br py:for="log in recipe.logs">${log.link}</br></td>
  </tr>
  <tr py:if="recipe.systems">
   <td class="title"><b>Possible Systems</b></td>
   <td class="value" colspan="8">
     ${recipe_systems}
   </td>
  </tr>
  <tr>
   <td colspan="9">
    <button class="all_show_recipe_${recipe.id}" id="all_recipe_${recipe.id}">
      Show All Results
    </button>
    <button py:if="recipe.is_failed()" class="fail_show_recipe_${recipe.id}" id="failed_recipe_${recipe.id}">
      Show Failed Results
    </button>
    <button class="hide_recipe_${recipe.id}" id="hide_recipe_${recipe.id}">
     Hide Results
    </button>
    <span class="hidden" id="task_items_loading_${recipe.id}"><img src="${tg.url('/static/images/ajax-loader.gif')}" /> </span>
   </td>
  </tr>
 </table>
 
 <div py:if="recipe_tasks_widget" class="hidden recipe-tasks fail_recipe_${recipe.id} recipe_${recipe.id}">
  <h2>Task Runs</h2> 
  <p class="hidden"> ${recipe_tasks_widget.link.display("I am hidden",action=tg.url('/tasks/do_search'), 
                                                        data=dict(recipe_id = recipe.id,
                                                                  tasks_tgp_order='id',
                                                                  tasks_tgp_limit=0),  
                                                        before="$('#task_items_loading_%s').removeClass('hidden')" % recipe.id, 
                                                        on_complete="$('#task_items_loading_%s').addClass('hidden');recipe_callback_%s();" % (recipe.id,recipe.id), 
                                                        update="task_items_%s" % recipe.id, 
                                                        attrs=dict(id='task_all_recipe_%s' % recipe.id,style='display:none;'))}
 </p>

  <div id="task_items_${recipe.id}"></div>
 </div>
</div>

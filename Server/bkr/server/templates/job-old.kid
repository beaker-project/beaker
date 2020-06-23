<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <script type="text/javascript" src="${tg.url('/static/javascript/primary_secondary.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/priority_manager_v4.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/rettag_manager_v2.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.timers-1.2.js')}"></script>
    <script type='text/javascript'>
//TODO I should move a lot of this out to a seperate JS file
 pri_manager = new PriorityManager()
 pri_manager.initialize()
 ackpanel  = new AckPanel()
      
 PARENT_ = 1
 NOT_PARENT = 0

 $(document).ready(function() {
    $('.ackpanel input').change(function () {
        var response_id = $(this).val()
        var parent_span = $(this).parents('span:first')
        var span_id = parent_span.attr('id') 
        var rs_id = span_id.replace(/^response_(\d{1,})$/,"$1") 
        ackpanel.update(rs_id,response_id) 
    })

    $("select[id^='priority']").change(function() {

        var callback = {'function' : ShowPriorityResults }
        callback['args'] = { 'element_id' : null, 'value' : null }
        callback['args']['element_id'] = $(this).attr("id")
        callback['args']['value'] = $(this).val()
        var success = pri_manager.changePriority($(this).attr("id"),$(this).val(),callback)
        //ShowPriorityResults($(this),$(this).val(),NOT_PARENT)
    })  


    $("a[id^='priority']").click(function() {
        var callback = {'function' : ShowPriorityResults }
        callback['args'] = {}
        callback['args']['value'] = $(this).attr("name")
        var success = pri_manager.changePriority($(this).attr("id"),$(this).attr("name"),callback)
        //ShowPriorityResults($(this),$(this).attr('name'),PARENT_);
    })

 });


 function ShowPriorityResults(elem_id,value,old_value,msg,success) { 
     jquery_obj = $("#"+elem_id)
     var id = elem_id.replace(/^.+?(\d{1,})$/,"$1") 
     var selector_msg = "msg[id='recipeset_priority_status_"+id+"']"
     var msg_text = ''
     if(success) {
         jquery_obj.val(value)
         var class_ = "success" 
         if (msg) {
             msg_text = msg
         } else {
             msg_text = "Priority has been updated" 
         }
     } else {
         var warn = 1
         var class_ = "warn" 
         if (old_value) {
             jquery_obj.val(old_value)
         }
         if (msg) {
             msg_text = msg
         } else {
             msg_text = "Unable to update priority" 
         }
        
     }
     $(selector_msg).text(msg_text) 
     $(selector_msg).fadeIn(1000)
     //$(selector_msg).show('slow')  
     $(selector_msg).removeAttr('class') 
     $(selector_msg).addClass(class_)     
     if (!warn) {
         $(selector_msg).fadeOut(1000)
     }
 }
    </script>
    <title>Job ${job.t_id} - ${job.whiteboard} | ${job.status} | ${job.result}</title>
</head>
<body class="with-localised-datetimes">
 <a data-toggle="collapse" href="#job_history">Toggle Job history</a>
 <div style='padding-bottom:0.25em' id="job_history" class="collapse">
   ${job_history_grid.display(job_history)}
 </div>
 <div id='dialog-confirm'> </div>
 <table class="table job">
 <tbody>
  <tr>
   <th>Job ID</th>
   <td>
    <a href="${tg.url('/jobs/%s' % job.id)}">${job.t_id}</a>
   </td>
   <th>Group</th>
   <td style="min-width: 100px;">
    <a py:if="job.group"
     href="${tg.url('/groups/edit?group_id=%d' % job.group.group_id)}">
     ${job.group}
    </a>
   </td>
   <th>Status</th>
   <td>
    <span py:if="job.is_dirty" class="statusDirty">Updating…</span>
    <span py:if="not job.is_dirty" class="status${job.status}">${job.status}</span>
   </td>
   <th>Result</th>
   <td class="result${job.result}">${job.result}</td>
  </tr>
  <tr>
   <th>Owner</th>
   <td>${job.owner.email_link}</td>
   <th>CC</th>
   <td>${'; '.join(job.cc)}</td>
   <th>Progress</th>
   <td>${job.progress_bar}</td>
   <th rowspan="2">Action(s)</th>
   <td rowspan="2">${action_widget(job, delete_action=delete_action, export=tg.url("/to_xml?taskid=%s" % job.t_id))}</td>
  </tr>
  <tr>
  <th>Retention Tag</th>
  <td py:if="job.can_change_retention_tag(tg.identity.user)">
    ${retention_tag_widget.display(value=job.retention_tag.id, job_id=job.id)}
  </td>
  <td py:if="not job.can_change_retention_tag(tg.identity.user)">
    ${retention_tag_widget.display(value=job.retention_tag.id,
        job_id=job.id,attrs=dict(disabled='1'))}
  </td>
  <th>Product</th>
  <td py:if="job.can_change_product(tg.identity.user)" colspan="3">
    ${product_widget.display(value=getattr(job.product,'id', 0), job_id=job.id)}
  </td>
  <td py:if="not job.can_change_product(tg.identity.user)" colspan="3">
    ${product_widget.display(value=getattr(job.product, 'id', 0),
        job_id=job.id, attrs=dict(disabled='1'))}
  </td>
  </tr>
  <tr>
   <th>Whiteboard</th>
   <td colspan="7">
     ${whiteboard_widget(value=job.whiteboard, job_id=job.id,
        readonly=not job.can_change_whiteboard(tg.identity.user))}
   </td>
  </tr>
  <tr py:if="job.can_change_priority(tg.identity.user) and job.is_queued()">
   ${job.priority_settings(prefix=u'priority_job_', colspan='3')}
    <script type='text/javascript'>
         pri_manager.register('priority_job_${job.id}','parent')
    </script> 
  </tr>
 </tbody>
 </table>
  <div py:for="recipeset in job.recipesets" class="recipeset">
    <?python 
        allowed_priorities = recipeset.allowed_priorities(tg.identity.user) 
    ?>   
 <div py:replace="recipeset_widget(recipeset=recipeset,priorities_list=allowed_priorities)">RecipeSet goes here</div>
   <div py:for="recipe in recipeset.recipes" py:strip="True" py:if="hasattr(recipe, 'guests')">
    <div py:content="recipe_widget(recipe=recipe)" class="recipe">Recipe goes here</div>
    <div py:for="guest in recipe.guests" class="recipe guest-recipe" py:content="recipe_widget(recipe=guest)">Guest goes here</div>
   </div>
  </div>
  ${hidden_id.display()}
</body>
</html>

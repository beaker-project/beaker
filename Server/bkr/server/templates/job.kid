<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <script type="text/javascript" src="${tg.url('/static/javascript/master_slave_v2.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/priority_manager_v4.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/rettag_manager_v2.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.timers-1.2.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.cookie.js')}"></script>
    <script type='text/javascript'>
//TODO I should move a lot of this out to a seperate JS file
 pri_manager = new PriorityManager()
 pri_manager.initialize()
 ackpanel  = new AckPanel()
      
 PARENT_ = 1
 NOT_PARENT = 0

 $(document).ready(function() {
    $('ul.ackpanel input').change(function () {  
        var response_id = $(this).val()
        changed_to_text = $(this).next().text().toLowerCase() 
        if (changed_to_text != 'ack' || changed_to_text != 'nak') { //this is a bit hackey, but basically if we're deselecting "Needs Review" we want to delete it.
            $(this).parents('ul:first').find('#unreal_response').parent().remove()
            $(this).parents('ul:first').find("a[id ^='comment_response_box']").removeClass('hidden')
        }
        var parent_span = $(this).parents('span:first')
        var span_id = parent_span.attr('id') 
        var rs_id = span_id.replace(/^response_(\d{1,})$/,"$1") 
        ackpanel.update(rs_id,response_id) 
    })

    $("a[id ^='comment_']").click(function () {
        var this_id = $(this).attr('id')
        var rs_id = this_id.replace(/^(.+)?_(\d{1,})$/,"$2")
        ackpanel.get_response_comment(rs_id)
    });



    $("#toggle_job_history").click(function() { $("#job_history").toggle() })
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

<script type="text/javascript">

</script>


<body class="flora">
 <a id='toggle_job_history' style="color: rgb(34, 67, 127); cursor: pointer;">Toggle Job history</a>
 <div style='padding-bottom:0.25em' id="job_history" class="hidden">
   ${job_history_grid.display(job_history)}
 </div>
 <div id='dialog-confirm'> </div>
 <table width="97%" class="show">
  <tr>
   <td class="title"><b>Job ID</b></td>
   <td class="value"><a class="list" href="${tg.url('/jobs/%s' % job.id)}">${job.t_id}</a></td>
   <td class="title"><b>Status</b></td>
   <td class="value">
    <span py:if="job.is_dirty" class="statusDirty">Updating…</span>
    <span py:if="not job.is_dirty" py:strip="True">${job.status}</span>
   </td>
   <td class="title"><b>Result</b></td>
   <td class="value">${job.result}</td>
  </tr>
  <tr>
   <td class="title"><b>Owner</b></td>
   <td class="value">${job.owner.email_link}</td>
   <td class="title"><b>Progress</b></td>
   <td class="value">${job.progress_bar}</td>
   <td class="title" rowspan="2"><b>Action(s)</b></td>
   <td class="value" rowspan="2">${action_widget(job, delete_action=delete_action, export=tg.url("/to_xml?taskid=%s" % job.t_id))}</td>
  </tr>
  <tr py:if="job.group">
   <td class='title'><b>Group</b></td>
   <td class="value">
    <a class="list"
     href="${tg.url('/groups/group_members/?id=%d' % job.group.group_id)}">
     ${job.group}
    </a>
   </td>
  </tr>
  <tr>
   <td class="title"><b>CC</b></td>
   <td class="value" colspan="3">${'; '.join(job.cc)}</td>
  </tr>
  <tr>
   <td class="title"><b>Whiteboard</b></td>
   <td class="value" colspan="3" style="vertical-align: top; white-space: normal;">${whiteboard_widget(value=job.whiteboard, job_id=job.id, readonly=not job.can_admin(tg.identity.user))}</td>
  </tr> 
  <tr>
  <td class="title"><b>Retention Tag</b></td>
  <td py:if="job.can_admin(tg.identity.user)" class='value' coslpan="3" style="vertical-align:top;">${retention_tag_widget.display(value=job.retention_tag.id, job_id=job.id)} </td>
 <td py:if=" not job.can_admin(tg.identity.user)" class='value' coslpan="3" style="vertical-align:top;">${retention_tag_widget.display(value=job.retention_tag.id, job_id=job.id,attrs=dict(disabled='1'))} </td>
  </tr>
  <tr>
  <td class="title"><b>Product</b></td>
  <td py:if="job.can_admin(tg.identity.user)" class='value' coslpan="3" style="vertical-align:top;">${product_widget.display(value=getattr(job.product,'id',0), job_id=job.id)}</td>
  <td py:if="not job.can_admin(tg.identity.user)" class='value' coslpan="3" style="vertical-align:top;">${product_widget.display(value=getattr(job.product,'id',0), job_id=job.id, attrs=dict(disabled='1'))}</td>
  </tr>
  <tr py:if="(job.access_rights(tg.identity.user) or job.can_admin(tg.identity.user)) and job.is_queued()">
  ${job.priority_settings(prefix=u'priority_job_', colspan='3')}

    <script type='text/javascript'>
         pri_manager.register('priority_job_${job.id}','parent')
    </script> 
  </tr>

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

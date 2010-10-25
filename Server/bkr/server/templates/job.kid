<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <script type="text/javascript" src="${tg.url('/static/javascript/master_slave_v2.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/priority_manager_v2.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/rettag_manager_v2.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.timers-1.2.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.cookie.js')}"></script>
    <script type='text/javascript'>
    //TODO I should move a lot of this out to a seperate JS file
 pri_manager = new PriorityManager()
 pri_manager.initialize()

 retentiontag_manager = new RetentionTagManager()
 retentiontag_manager.initialize()

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


    $("select[id^='retentiontag']").change(function() {

        var callback = {'function' : ShowRetentionTagResults }
        callback['args'] = { 'element_id' : null, 'value' : null }
        callback['args']['element_id'] = $(this).attr("id")
        callback['args']['value'] = $(this).val()
        var success = retentiontag_manager.changeValue($(this).attr("id"),$(this).val(),callback)
        //ShowPriorityResults($(this),$(this).val(),NOT_PARENT)
    })  

    $("a[id^='retentiontag']").click(function() {
        var callback = {'function' : ShowRetentionTagResults }
        callback['args'] = {}
        callback['args']['value'] = $(this).attr("name")
        var success = retentiontag_manager.changeValue($(this).attr("id"),$(this).attr("name"),callback)
        //ShowPriorityResults($(this),$(this).attr('name'),PARENT_);
    })

    

 });

 function ShowRetentionTagResults(elem_id,value,old_value,msg,success) { 
     jquery_obj = $("#"+elem_id)
     var id = elem_id.replace(/^.+?(\d{1,})$/,"$1") 
     var selector_msg = "msg[id='recipeset_tag_status_"+id+"']" 
     var msg_text = ''
     if(success) {
         jquery_obj.val(value)
         var class_ = "success" 
         if (msg) {
             msg_text = msg
         } else {
             msg_text = "Tag has been updated" 
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
             msg_text = "Unable to update Tag" 
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
 <table width="97%" class="show">
  <tr>
   <td class="title"><b>Job ID</b></td>
   <td class="value"><a class="list" href="${tg.url('/jobs/%s' % job.id)}">${job.t_id}</a></td>
   <td class="title"><b>Status</b></td>
   <td class="value">${job.status}</td>
   <td class="title"><b>Result</b></td>
   <td class="value">${job.result}</td>
  </tr>
  <tr>
   <td class="title"><b>Owner</b></td>
   <td class="value">${job.owner}</td>
   <td class="title"><b>Progress</b></td>
   <td class="value">${job.progress_bar}</td>
   <td class="title"><b>Action(s)</b></td>
   <td class="value">${job.action_link}</td>
  </tr>
  <tr>
   <td class="title"><b>Whiteboard</b></td>
   <td class="value" colspan="3" style="vertical-align: top;">${whiteboard_widget(value=job.whiteboard, job_id=job.id, readonly=not job.can_admin(user))}</td>
  </tr> 
  <tr py:if="job.access_rights(user)">
  ${job.retention_settings(prefix=u'retentiontag_job_', colspan='3')}

    <script type='text/javascript'>
        retentiontag_manager.register('retentiontag_job_${job.id}','master')
    </script>
  </tr>
  <tr py:if="job.access_rights(user) and job.is_queued()">
  ${job.priority_settings(prefix=u'priority_job_', colspan='3')}

    <script type='text/javascript'>
         pri_manager.register('priority_job_${job.id}','parent')
    </script> 
  </tr>

 </table>
  <div py:for="recipeset in job.recipesets" class="recipeset">
    <?python 
        allowed_priorities = recipeset.allowed_priorities(user) 
        if allowed_priorities:
            priorities_list = [(elem.id,elem.priority) for elem in allowed_priorities]
        else: priorities_list = None
    ?>   
 <div py:content="recipeset_widget(recipeset=recipeset,priorities_list=priorities_list)">RecipeSet goes here</div>
   <div py:for="recipe in recipeset.recipes" class="recipe">
    <div py:content="recipe_widget(recipe=recipe)">Recipe goes here</div>
   </div>
  </div>
</body>
</html>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <script type="text/javascript" src="${tg.url('/static/javascript/priority_manager.js')}"></script>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.timers-1.2.js')}"></script>
    <script type='text/javascript'>
 pri_manager = new PriorityManager()
 pri_manager.initialize()
       
 PARENT_ = 1
 NOT_PARENT = 0
 

 $(document).ready(function() {
    ShowResults();
    $("input[@name='results']").change(ShowResults);
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
     var selector_msg = "msg[id='recipeset_status_"+id+"']"
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
     $(selector_msg).show('slow')  
     $(selector_msg).removeAttr('class') 
     $(selector_msg).addClass(class_)     
     if (!warn) {
         jquery_obj.oneTime(2000, "hide", function() { 
             $(selector_msg).hide('slow') 
         });
     }
 }

 function ShowResults()
 {
    switch ($("input[@name='results']:checked").val())
    {
        case 'all':
            $('.fail').show();
            $('.pass').show();
        break;
        case 'fail':
            $('.fail').show();
            $('.pass').hide();
        break;
    }
 }
    </script>
    <title>Job ${job.t_id} - ${job.whiteboard} | ${job.status} | ${job.result}</title>
</head>

 <?python
    if job.result:
        default = job.result.result == 'Pass' and 'ShowAll' or 'ShowFail'
    else:
        default = 'ShowAll'
 ?>

<script type="text/javascript">

</script>


<body class="flora">
 <form>
  <input id="results_all" type="radio" name="results" value="all" checked="${(None, '')[default == 'ShowAll']}" />
  <label for="results_all">All results</label>
  <input id="results_fail" type="radio" name="results" value="fail" checked="${(None, '')[default == 'ShowFail']}" />
  <label for="results_fail">Only failed items</label>
  <!-- <input id="results_ackneeded" type="radio" name="results" value="ackneeded" />
  <label for="results_ackneeded">Failed items needing review</label> -->
  <a id='toggle_job_history' style="color: rgb(34, 67, 127); cursor: pointer;">Toggle Job history</a>
 </form>
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
   <td class="value" colspan="3">${job.whiteboard}</td>
   <span py:if="job.is_queued() and job.access_priority(user)"> 
    <td class="title"><b>Set all RecipeSet priorities</b></td> 
     <td class="value"><a py:for="p in priorities" class="list" style="color: #22437F;cursor:pointer" name="${p.id}" id="priority_job_${job.id}">${p.priority}<br /></a></td>
      <script type='text/javascript'>
       pri_manager.register('priority_job_${job.id}','parent')
      </script>
   </span>
  </tr>
 </table>
  <div py:for="recipeset in job.recipesets" class="recipeset">
    <?python 
        allowed_priorities = recipeset.allowed_priorities(user) 
        if allowed_priorities:
            priorities_list = [(elem.id,elem.priority) for elem in allowed_priorities]
        else: priorities_list = None
    ?>   
   <table width="97%">
    <a name="RS_${recipeset.id}" />
    <tr>
     <td class="title"><b>RecipeSet ID</b></td>
     <td class="value">${recipeset.t_id}</td>  
   <span py:if="recipeset.is_queued() and priorities_list"> 
   <td class="title"><msg id="recipeset_status_${recipeset.id}" class='hidden'></msg> <b>Priority</b></td>  
   <td class="value">${priority_widget.display(obj=recipeset,id_prefix='priority_recipeset',priorities=priorities_list)}</td>
    <script type='text/javascript'>
       pri_manager.register('priority_recipeset_${recipeset.id}','recipeset')
    </script>
   </span>
    </tr>
   </table>
   <div py:for="recipe in recipeset.recipes" class="recipe">
    <div py:content="recipe_widget(recipe=recipe)">Recipe goes here</div>
   </div>
  </div>
</body>
</html>

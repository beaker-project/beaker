<div xmlns:py="http://purl.org/kid/ns#">
 <table style="width: 100%;" id="RS_${recipeset.id}">
  <tr>
   <td class="title"><b>RecipeSet ID</b></td>
   <td class="value">${recipeset.t_id}</td><td
       style='min-width:30em'>
     <span id="response_${recipeset.id}" class="form-inline" py:if="can_ack_nak">
    ${ack_panel_widget.display(recipeset.id, name='response_box_%s' % recipeset.id)}
     </span>
   </td>
   <span py:if="recipeset.is_queued() and priorities_list">
    <td class="title"><msg id="recipeset_priority_status_${recipeset.id}" class='hidden'></msg> <b>Priority</b></td>
    <td class="value">${priority_widget.display(obj=recipeset,id_prefix='priority_recipeset',priorities=priorities_list)}</td>
    <script type='text/javascript'>
       pri_manager.register('priority_recipeset_${recipeset.id}','recipeset')
    </script>
   </span> 
   <td class="title"><b>Action</b></td>
   <td class="value">${action_widget.display(recipeset)}</td>
  </tr>
 </table>
</div>

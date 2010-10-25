<div xmlns:py="http://purl.org/kid/ns#">
 <table width="97%">
 <a name="RS_${recipeset.id}" />
  <tr>
   <td class="title"><b>RecipeSet ID</b></td>
   <td class="value">${recipeset.t_id}</td><td py:if="recipeset.is_owner(tg.identity.user) or 'admin' in tg.identity.groups" style='min-width:30em'>
     <span id="response_${recipeset.id}">
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
   <span py:if="recipeset.is_owner(tg.identity.user) or 'admin' in tg.identity.groups">
   <td class="title"><msg id="recipeset_tag_status_${recipeset.id}" class='hidden'></msg> <b>Retention Tag</b></td>  
   <td class="value">${retentiontag_widget.display(obj=recipeset,id_prefix='retentiontag_recipeset')}</td>
   <script type='text/javascript'>
       retentiontag_manager.register('retentiontag_recipeset_${recipeset.id}','slave')
   </script>
   </span>
   <td class="title"><b>Action</b></td>
   <td class="value">${recipeset.action_link}</td>
  </tr>
  <tr py:if="recipeset.deleted is not None">
  <td colspan='7' align='center'><msg class='warn'>Recipe and Task logs have been deleted: ${recipeset.deleted}</msg> </td>
  </tr>
 </table>
</div>

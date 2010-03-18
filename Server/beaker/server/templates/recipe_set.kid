<div xmlns:py="http://purl.org/kid/ns#">
 <table width="97%">
  <tr>
   <td class="title"><b>RecipeSet ID</b></td>
   <td class="value">${recipeset.t_id}</td>
   <span py:if="recipeset.is_queued()">
     <td class="title"><b>Priority</b></td>
     <td class="value">${priority_widget.display(obj=recipeset)}
 </td>
   </span>
  </tr>
 </table>
</div>

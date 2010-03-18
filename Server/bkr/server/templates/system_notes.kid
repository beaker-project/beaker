<form xmlns:py="http://purl.org/kid/ns#"
 name="${name}"
 action="${tg.url(action)}"
 method="${method}" width="100%">
 <div py:if="not readonly">
   ${display_field_for("note")}
   ${display_field_for("id")}
    <a class="button" href="javascript:document.${name}.submit();">Add ( + )</a>
  <br/>
  <br/>
 </div>
 <table class="list">
  <?python row_color = "#F1F1F1" ?>
  <div py:for="note in notes">
   <tr class="list" bgcolor="${row_color}">
    <th class="list">User</th>
    <td class="list">${note.user}</td>
    <th class="list">Created</th>
    <td class="list">${note.created}</td>
   </tr>
   <tr>
    <th class="list">Note</th>
    <td class="list" colspan="3"><pre>${note.text}</pre></td>
   </tr>
   <tr>
    <td>&nbsp;</td>
   </tr>
  </div>
 </table>
</form>

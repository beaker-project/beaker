<form xmlns:py="http://purl.org/kid/ns#"
 name="${name}"
 action="${tg.url(action)}"
 method="${method}" width="100%">
 <table class="list">
  <tr class="list">
   <th class="list">
    <b>Tag</b>
   </th>
   <th class="list">
    <b>&nbsp;</b>
   </th>
  </tr>
  <tr class="list" py:if="not readonly">
   <td class="list">
    ${display_field_for("tag")}
   </td>
   <td class="list">
    &nbsp;
   </td>
   <td class="list">
    ${display_field_for("id")}
    <a class="button" href="javascript:document.${name}.submit();">Add ( + )</a>
   </td>
  </tr>
  <?python row_color = "#f1f1f1" ?>
  <tr class="list" bgcolor="${row_color}" py:for="tag in tags">
   <td class="list">
    ${tag}
   </td>
   <td class="list">
    <a py:if="not readonly" class="button" href="${tg.url('./tag_remove', id=value_for('id'), tag=tag)}">Delete ( - )</a>
   </td>
    <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr>
 </table>
</form>

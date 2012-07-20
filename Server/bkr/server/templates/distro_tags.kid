<span xmlns:py="http://purl.org/kid/ns#" py:strip='1'>
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
   <form name="${name}" action="${tg.url(action)}" method="POST">
    ${display_field_for("id")}
    <input type='hidden' id="${name}_${tag.name}_${tag.text_field.name}_hidden" name="${tag.name}.text" />
    <a class="button" href="javascript:document.${name}.submit();" onclick="populate_form_elements(this.parentNode); return true;">Add ( + )</a>
    </form>
   </td>
  </tr>
  <?python row_color = "#f1f1f1" ?>
  <tr class="list" bgcolor="${row_color}" py:for="tag in tags">
   <td class="list">
    ${tag}
   </td>
   <td class="list">
    <span py:if="not readonly" py:strip='1'>
     ${delete_link.display(dict(id=value_for('id'), tag=tag), action=tg.url('tag_remove'))}
    </span>
   </td>
    <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr>
 </table>
</span>

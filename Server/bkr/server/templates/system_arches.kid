 <table class="list" width="100%" xmlns:py='http://purl.org/kid/ns#'>
  <tr class="list">
   <th class="list">
    <b>Arch</b>
   </th>
   <th class="list">
    <b>&nbsp;</b>
   </th>
  </tr>
  <tr class="list" py:if="not readonly">
   <td class="list">
    ${display_field_for("arch")}
   </td>
   <td class="list">
    <form  name="${name}" action="${tg.url(action)}" method="POST">
     <script src="${tg.url('/static/javascript/magic_forms.js')}" type='text/javascript'/>
     <input type='hidden'
      id="${name}_${arch.name}_${arch.text_field.name}_hidden"
      name="${arch.name}.text" />
     ${display_field_for("id")}
     <a onclick='populate_form_elements(this.parentNode);return true;' href="javascript:document.${name}.submit();">Add ( + )</a>
    </form>
   </td>
  </tr>
  <?python row_color = "#f1f1f1" ?>
  <tr class="list" bgcolor="${row_color}" py:for="arch in arches">
   <td class="list">
    ${arch.arch}
   </td>
   <td class="list">
    <span py:if='not readonly' py:strip='1'>
      ${delete_link.display(dict(system_id=value_for('id'), arch_id=arch.id),
          attrs=dict(class_='link'), action=tg.url('/arch_remove'))}
    </span>
   </td>
    <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr>
 </table>

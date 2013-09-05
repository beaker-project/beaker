<table class="table table-one-line-per-row" xmlns:py='http://purl.org/kid/ns#' style="max-width: 30em;">
  <thead>
    <tr>
      <th>Arch</th>
      <th/>
    </tr>
  </thead>
  <tbody>
    <tr py:if="not readonly">
      <td>
    ${display_field_for("arch")}
      </td>
      <td>
    <form  name="${name}" action="${action}" method="POST" onsubmit="populate_form_elements(this); return true;">
     <script src="${tg.url('/static/javascript/magic_forms.js')}" type='text/javascript'/>
     <input type='hidden'
      id="${name}_${arch.name}_${arch.text_field.name}_hidden"
      name="${arch.name}.text" />
     ${display_field_for("id")}
     <button class="btn btn-primary" type="submit"><i class="icon-plus" /> Add</button>
    </form>
   </td>
    </tr>
    <tr py:for="arch in arches">
      <td>
    ${arch.arch}
      </td>
      <td>
    <span py:if='not readonly' py:strip='1'>
      ${delete_link.display(dict(system_id=value_for('id'), arch_id=arch.id),
          action=tg.url('/arch_remove'))}
    </span>
   </td>
  </tr>
  </tbody>
 </table>

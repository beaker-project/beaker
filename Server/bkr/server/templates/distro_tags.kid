<table xmlns:py="http://purl.org/kid/ns#" class="table table-striped">
  <thead><tr><th>Tag</th><th></th></tr></thead>
  <tbody>
    <tr py:if="not readonly">
      <td>${display_field_for("tag")}</td>
      <td>
   <form name="${name}" action="${tg.url(action)}" method="POST">
    ${display_field_for("id")}
    <input type='hidden' id="${name}_${tag.name}_${tag.text_field.name}_hidden" name="${tag.name}.text" />
    <a class="btn" href="javascript:document.${name}.submit();" onclick="populate_form_elements(this.parentNode); return true;"><i class="fa fa-plus"/> Add</a>
    </form>
      </td>
    </tr>
    <tr py:for="tag in tags">
      <td>${tag}</td>
      <td>
    <span py:if="not readonly" py:strip='1'>
     ${delete_link.display(dict(id=value_for('id'), tag=tag), action=tg.url('tag_remove'))}
    </span>
      </td>
    </tr>
  </tbody>
</table>

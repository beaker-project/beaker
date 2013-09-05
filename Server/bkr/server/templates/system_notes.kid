<div xmlns:py='http://purl.org/kid/ns#'>
 <script type='text/javascript' src="${tg.url('/static/javascript/system_notes_v2.js')}" />
 <script type='text/javascript' src="${tg.url('/static/javascript/util.js')}" />
    <form name="${name}" action="${action}" method="${method}" py:if="not readonly">
   ${display_field_for("note")}
   ${display_field_for("id")}
   <a class="btn btn-primary" href="javascript:document.${name}.submit();"><i class="icon-plus"/> Add</a>
    </form>
  <table class="table table-striped">
    <thead>
      <tr>
        <th>User</th>
        <th>Created</th>
        <th>Note</th>
        <th/>
      </tr>
    </thead>
    <tbody>
      <tr py:for="note in notes" id="note_${note.id}"
          py:attrs="note.deleted and {'style': 'display: none;', 'class': 'note_deleted'} or {}">
        <td>${note.user.email_link}</td>
        <td class="datetime">${note.created}</td>
        <td py:content="note.html" />
        <td>
      <span py:if="not readonly and not note.deleted" py:strip="1">
       <script type='text/javascript'>
        function delete_note(id) {
            function inner() {
                note_delete_success(id)
             }
             return inner
         }
        </script>
        ${delete_link(action=tg.url('/delete_note'), data=dict(id=note.id),
            callback="delete_note(%s)" % note.id, 
            attrs=dict(id="delete_note_%s" % note.id),
            action_text='Delete')}
      </span>
        </td>
      </tr>
    </tbody>
 </table>

  <a py:if="not readonly and [1 for note in notes if note.deleted]" class="btn" href="#" onclick="toggle_deleted_notes(); return false;">Toggle deleted notes</a>
  <a py:if="readonly or not [1 for note in notes if note.deleted]" style='display:none;' class="btn" href="#" id='toggle_deleted_notes' onclick="toggle_deleted_notes(); return false;">Toggle deleted notes</a>

</div>

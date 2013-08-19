<div xmlns:py='http://purl.org/kid/ns#'>
 <script type='text/javascript' src="${tg.url('/static/javascript/system_notes.js')}" />
 <script type='text/javascript' src="${tg.url('/static/javascript/util.js')}" />
 <form name="${name}" action="${tg.url(action)}" method="${method}">
  <div py:if="not readonly">
   ${display_field_for("note")}
   ${display_field_for("id")}
   <a class="button" href="javascript:document.${name}.submit();">Add ( + )</a>
  </div>
 </form>
  <br/>
  <br/>
 <table class="list">
  <?python row_color = "#F1F1F1" ?>
  <div py:for="note in notes" py:strip="1">
   <tbody py:if="not note.deleted" id="note_${note.id}">
   <tr class="list" bgcolor="${row_color}">
    <th class="list">User</th>
    <td class="list">${note.user}</td>
    <th class="list">Created</th>
    <td class="list"><span class="datetime">${note.created}</span></td>
   </tr>
   <tr>
    <th class="list">Note</th>
    <td class="list" colspan="3">
      <div py:content="note.html" />
      <span py:if="not readonly" py:strip="1">
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
            attrs=dict(class_='link', id="delete_note_%s" % note.id),
            action_text='(Delete this note)')}
      </span>
    </td>
   </tr>
   <tr>
    <td>&nbsp;</td>
   </tr>
   </tbody>

   <tbody py:if="note.deleted" style='display:none' id="note_deleted_${note.id}">
   <tr class="list" bgcolor="${row_color}">
    <th class="list">User</th>
    <td class="list">${note.user}</td>
    <th class="list">Created</th>
    <td class="list"><span class="datetime">${note.created}</span></td>
    <th class="list">Deleted</th>
    <td class="list"><span class="datetime">${note.deleted}</span></td>
   </tr>
   <tr>
    <th class="list">Note</th>
    <td class="list" colspan="3">
      <div py:content="note.html" />
    </td>
   </tr>
   <tr>
    <td>&nbsp;</td>
   </tr>
   </tbody>
   </div>
 </table>

  <a py:if="not readonly and [1 for note in notes if note.deleted]" style='display:inline;' class="link" id='toggle_deleted_notes' onclick="javascript:toggle_deleted_notes()">Toggle deleted notes</a>
  <a py:if="readonly or not [1 for note in notes if note.deleted]" style='display:none;' class="link" id='toggle_deleted_notes' onclick="javascript:toggle_deleted_notes()">Toggle deleted notes</a>

</div>

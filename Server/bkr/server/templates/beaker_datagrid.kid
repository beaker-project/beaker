<table xmlns:py="http://purl.org/kid/ns#" id="${name}" class="list" cellpadding="0" cellspacing="1" border="0">
  <thead py:if="columns" class="list">
    <tr>
      <th py:for="i, col in enumerate(columns)" class="list" py:content="col.title"/>
    </tr>
  </thead>
  <tbody>
    <tr py:for="i, row in enumerate(value)" class="${i%2 and 'odd' or 'even'}">
      <td class="list" py:for="col in columns" align="${col.get_option('align', None)}">
        <span class="datetime" py:strip="not col.get_option('datetime', False)">
            ${col.get_field(row)}
        </span>
      </td>
    </tr>
  </tbody>
</table>


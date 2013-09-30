<table xmlns:py="http://purl.org/kid/ns#" id="${name}" class="table table-striped table-hover table-one-line-per-row">
  <thead py:if="columns">
    <tr>
      <th py:for="col in columns" py:content="col.title"/>
    </tr>
  </thead>
  <tbody>
    <tr py:for="row in value">
      <td py:for="col in columns" align="${col.get_option('align', None)}"><span class="datetime" py:strip="not col.get_option('datetime', False)">${col.get_field(row)}</span></td>
    </tr>
  </tbody>
</table>


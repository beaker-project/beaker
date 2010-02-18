<table xmlns:py="http://purl.org/kid/ns#" id="${name}" class="list" cellpadding="0" cellspacing="1" border="0">
<thead py:if="columns">
  <tr>
    <th py:for="i, col in enumerate(columns)" class="list" py:content="col.title"/>
  </tr>
</thead>
<tbody>
  <tr py:for="i, row in enumerate(value)" class="${i%2 and 'odd' or 'even'}">
  
    <td style="vertical-align:center" py:for="col in columns" align="${col.get_option('align', None)}" py:content="col.get_field(row)"/>
  </tr>
</tbody>
</table>

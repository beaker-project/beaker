
<table xmlns:py="http://purl.org/kid/ns#" id="${name}" class="list" cellpadding="0" cellspacing="1" border="0">
<?python
show = columns and show_headers
?>
<thead py:if="show">
  <tr>
    <th py:for="i, col in enumerate(columns)" class="list" style='padding-left:0px' py:if="col.title != 'none'" py:content="col.title"/>
  </tr>
</thead>
<thead py:if="not show">
  <tr>
    <th py:for="i, col in enumerate(columns)"  class="list hidden_header" style='padding-left:0px' py:if="col.title != 'none'" py:content=""/>
  </tr>
</thead>
<tbody>
  <tr py:for="i, row in enumerate(value)" > 
    <td py:for="col in columns" align="${col.get_option('align', None)}" py:content="col.get_field(row)"/>
  </tr>
</tbody>
</table>

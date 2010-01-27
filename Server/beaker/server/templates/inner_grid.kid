
<table xmlns:py="http://purl.org/kid/ns#" id="${name}" class="list" cellpadding="0" cellspacing="1" border="0">
<?python
show_headers = columns and show_headers

?>
<thead py:if="show_headers">
  <tr>
    <th py:for="i, col in enumerate(columns)" class="list" py:if="col.title != 'none'" py:content="col.title"/>
  </tr>
</thead>
<tbody>
  <tr py:for="i, row in enumerate(value)" > 
    <td py:for="col in columns" align="${col.get_option('align', None)}" py:content="col.get_field(row)"/>
  </tr>
</tbody>
</table>

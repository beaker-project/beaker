
<table xmlns:py="http://purl.org/kid/ns#" id="${name}" class="list" cellpadding="0" cellspacing="1" border="0">
<?python
show = columns and show_headers
import re
?>
<thead py:if="show">
  <tr>
    <th py:for="col in columns" class="whiteboard-header" py:content="re.sub('_0\.\d{1,}$','', col.title)"/>
  </tr>
</thead>
<thead py:if="not show">
  <tr>
    <th py:for="col in columns"  class="whiteboard-header" />
  </tr>
</thead>
<tbody>
  <tr py:for="i, row in enumerate(value)" > 
    <td py:for="col in columns" align="${col.get_option('align', None)}" py:content="col.get_field(row)" style='text-align:center' />
  </tr>
</tbody>
</table>

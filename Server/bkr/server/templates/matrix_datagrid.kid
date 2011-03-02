<table xmlns:py="http://purl.org/kid/ns#" id="${name}" cellpadding="0" cellspacing="0" border="0" >
<script type='text/javascript' src='/static/javascript/jquery.dataTables.js' />
<script type='text/javascript' src='/static/javascript/FixedColumns.js' />

<script type='text/javascript'>

$(document).ready( function() {

var oTable = $('#matrix_datagrid').dataTable( {
        "sScrollX": "100%",
        "sScrollY" : "600px",
        "bScrollCollapse": true,
        "bPaginate": false,
        "bFilter": false,
        "sDom": '&lt;"top"&gt;rt&lt;"bottom"flp&gt;&lt;"clear"&gt;'
    } );

    new FixedColumns( oTable );
});
</script>
<thead py:if="columns">
 <?python import re ?>
  <tr py:if="outer_headers">
    <th py:for="pos,header_colspan in enumerate(outer_headers)" py:if="pos == TASK_POS" class="matrix-header task-header outer-header cell-border border-white" colspan="${header_colspan[1]}" py:content="header_colspan[0]"/>
    <th py:for="pos,header_colspan in enumerate(outer_headers)" py:if="pos != TASK_POS" class="matrix-header outer-header cell-border border-white" colspan="${header_colspan[1]}" py:content="header_colspan[0]"/>
  </tr>
  <tr>
    <th py:for="pos,col in enumerate(columns)" py:if="pos == TASK_POS" class="matrix-whiteboard cell-border border-coloured"/>
    <th py:for="pos,col in enumerate(columns)" py:if="pos != TASK_POS" class="matrix-whiteboard cell-border border-coloured" py:content="re.sub('_0\.\d{1,}$','', col.title)"/>
  </tr>
</thead>
<tbody>
  <tr py:for="i, row in enumerate(value)" class="${i%2 and 'odd' or 'even'}">
    <td py:for="pos,col in enumerate(columns)" py:if="pos == TASK_POS" align="${col.get_option('align', None)}" py:content="col.get_field(row)"  class='task-name cell-border' />
    <td py:for="pos,col in enumerate(columns)" py:if="pos != TASK_POS" align="${col.get_option('align', None)}" py:content="col.get_field(row)"  class='cell-border results' />
  </tr>
</tbody>
</table>

<table xmlns:py="http://purl.org/kid/ns#" id="${name}" cellpadding="0" cellspacing="0" border="0" >
<script type='text/javascript' src='/static/javascript/jquery.dataTables-1.9.4.min.js' />
<script type='text/javascript' src='/static/javascript/dataTables.fixedColumns-3429ac3.js' />

<script type='text/javascript'>

$(document).ready( function() {

var oTable = $('#matrix_datagrid').dataTable( {
        "sScrollX": "100%",
        "sScrollY" : "600px",
        "bScrollCollapse": true,
        "bSort": false,
        "bPaginate": false,
        "bFilter": false,
        "sDom": '&lt;"top"&gt;rt&lt;"bottom"flp&gt;&lt;"clear"&gt;',
        "fnRowCallback": function (row, data, index, index_full) {
            $(row).addClass(i % 2 ? 'odd' : 'even');
        },
        "fnDrawCallback": function () {
            // hack to fix horizontal scrollbars (bug in FixedColumns?)
            $('.dataTables_scrollBody').css('overflow-x', 'hidden');
        },
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
  <tr py:for="row in value">
    <td py:for="pos,col in enumerate(columns)" py:if="pos == TASK_POS" align="${col.get_option('align', None)}" py:content="col.get_field(row)"  class='task-name cell-border' />
    <td py:for="pos,col in enumerate(columns)" py:if="pos != TASK_POS" align="${col.get_option('align', None)}" py:content="col.get_field(row)"  class='cell-border results' />
  </tr>
</tbody>
</table>

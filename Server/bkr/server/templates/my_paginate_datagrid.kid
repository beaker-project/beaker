<div xmlns:py="http://purl.org/kid/ns#">
  <div class="list">
    <span py:if="tg.paginate.limit > 0" style="margin-right:0.5em;">
    <span py:if="tg.paginate.page_count > 1">
      <?python 
        from re import sub 
        if tg.request.query_string:
            tg.request.query_string = sub('\w{1,}_tgp_limit=\d{1,}','',tg.request.query_string)
      ?> 
      <a py:if="tg.request.query_string" href="${tg.url(tg.request.path_info)}?${tg.request.query_string}&amp;tg_paginate_limit=0">Show all</a>
      <a py:if="not tg.request.query_string" href="${tg.url(tg.request.path_info)}?tg_paginate_limit=0">Show all</a></span>
    </span>
    <span py:if="tg.paginate.href_prev">
        <a href="${tg.paginate.href_first}">&lt;&lt;</a>
        <a href="${tg.paginate.href_prev}">&lt;</a>
    </span>
    <span py:if="tg.paginate.page_count > 1" py:for="page in tg.paginate.pages">
      <span py:if="page == tg.paginate.current_page" py:replace="page"/>
      <span py:if="page != tg.paginate.current_page">
         <a href="${tg.paginate.get_href(page)}">${page}</a>
      </span>
    </span>
    <span py:if="tg.paginate.href_next">
      <a href="${tg.paginate.href_next}">&gt;</a>
      <a href="${tg.paginate.href_last}">&gt;&gt;</a>
    </span>
  </div>
  <table id="${name}" class="list">
    <thead py:if="columns" class="list">
      <th py:for="i, col in enumerate(columns)" class="list">
        <a class="head_list" py:if="col.get_option('sortable', False) and getattr(tg, 'paginate', False)"
            href="${tg.paginate.get_href(1, col.name, col.get_option('reverse_order', False))}">${col.title}</a>
        <span py:if="not getattr(tg, 'paginate', False) or not col.get_option('sortable', False)" py:replace="col.title"/>
      </th>
    </thead>
    <tr py:for="i, row in enumerate(value)" class="${i%2 and 'odd' or 'even'}">
      <td py:for="col in columns" class="list">
        ${col.get_field(row)}
      </td>
    </tr>
  </table>
</div>


<div xmlns:py="http://purl.org/kid/ns#">
  <div class="list">
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
  <table id="${name}" class="list highlight-row">
    <thead py:if="columns" class="list">
      <tr>
        <th py:for="i, col in enumerate(columns)" class="list">
          <a class="head_list" py:if="col.get_option('sortable', False) and getattr(tg, 'paginate', False)"
              href="${tg.paginate.get_href(1, col.name, col.get_option('reverse_order', False))}">${col.title}</a>
          <span py:if="not getattr(tg, 'paginate', False) or not col.get_option('sortable', False)" py:replace="col.title"/>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr py:for="i, row in enumerate(value)" class="${i%2 and 'odd' or 'even'}">
        <td py:for="col in columns" class="list">
          <span class="datetime" py:strip="not col.get_option('datetime', False)">
              ${col.get_field(row)}
          </span>
        </td>
      </tr>
    </tbody>
  </table>
  <div class="list">
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
</div>


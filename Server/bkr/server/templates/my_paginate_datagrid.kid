<div xmlns:py="http://purl.org/kid/ns#">
  <div class="pagination pagination-right">
    <div class="pagination-beside">
        <span class="item-count">Items found: ${tg.paginate.row_count}</span>
    </div>
    <ul py:if='tg.paginate.page_count > 1'>
        <span py:if='(tg.paginate.page_count &gt; 5) and
                (1 not in tg.paginate.pages)' py:strip='1'>
            <li>
                <a py:if="tg.paginate.pages[0] - 1 &gt; 1"
                    href="${tg.paginate.href_first}">1&#8230;</a>
                <a py:if="tg.paginate.pages[0] - 1 &lt; 2"
                    href="${tg.paginate.href_first}">1</a>
            </li>
        </span>
        <span py:if="tg.paginate.page_count > 1"
            py:for="page in tg.paginate.pages" py:strip='1'>
            <li py:if="page == tg.paginate.current_page" class="active">
                <span>${page}</span>
            </li>
            <li py:if="page != tg.paginate.current_page">
                <a href="${tg.paginate.get_href(page)}">${page}</a>
            </li>
        </span>
        <span py:if='tg.paginate.page_count &gt; 5 and tg.paginate.page_count
            not in tg.paginate.pages' py:strip='1'>
            <li>
                <a py:if='(tg.paginate.page_count - tg.paginate.pages[-1]) &gt; 1'
                    href="${tg.paginate.href_last}">
                    &#8230;${tg.paginate.page_count}
                </a>
                <a py:if='(tg.paginate.page_count - tg.paginate.pages[-1]) &lt; 2'
                    href="${tg.paginate.href_last}">${tg.paginate.page_count}</a>
            </li>
        </span>
    </ul>
  </div>
  <table id="${name}" class="table table-striped table-hover table-condensed table-one-line-per-row">
    <thead py:if="columns">
      <tr>
        <th py:for="col in columns">
          <a py:strip="not col.get_option('sortable', False)"
              href="${tg.paginate.get_href(1, col.name, col.get_option('reverse_order', False))}">${col.title}</a>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr py:for="row in value">
        <td py:for="col in columns">
          <span class="datetime" py:strip="not col.get_option('datetime', False)">
              ${col.get_field(row)}
          </span>
        </td>
      </tr>
    </tbody>
  </table>
  <div py:if="add_action" style="float: left;">
    <a class="btn btn-primary" href="${tg.url(add_action)}"><i class="fa fa-plus"/> Add</a>
  </div>
  <div py:if="add_script" style="float: left;">
    <a class="btn btn-primary" href="#" onclick="${add_script}; return false;"><i class="fa fa-plus"/> Add</a>
  </div>
  <div class="pagination pagination-right">
    <div class="pagination-beside">
        <span class="item-count">Items found: ${tg.paginate.row_count}</span>
    </div>
    <ul py:if='tg.paginate.page_count > 1' >
        <span py:if='(tg.paginate.page_count &gt; 5) and
                (1 not in tg.paginate.pages)' py:strip='1'>
            <li>
                <a py:if="tg.paginate.pages[0] - 1 &gt; 1"
                    href="${tg.paginate.href_first}">1&#8230;</a>
                <a py:if="tg.paginate.pages[0] - 1 &lt; 2"
                    href="${tg.paginate.href_first}">1</a>
            </li>
        </span>
        <span py:if="tg.paginate.page_count > 1"
            py:for="page in tg.paginate.pages" py:strip='1'>
            <li py:if="page == tg.paginate.current_page" class="active">
                <span>${page}</span>
            </li>
            <li py:if="page != tg.paginate.current_page">
                <a href="${tg.paginate.get_href(page)}">${page}</a>
            </li>
        </span>
        <span py:if='tg.paginate.page_count &gt; 5 and tg.paginate.page_count
            not in tg.paginate.pages' py:strip='1'>
            <li>
                <a py:if='(tg.paginate.page_count - tg.paginate.pages[-1]) &gt; 1'
                    href="${tg.paginate.href_last}">
                    &#8230;${tg.paginate.page_count}
                </a>
                <a py:if='(tg.paginate.page_count - tg.paginate.pages[-1]) &lt; 2'
                    href="${tg.paginate.href_last}">${tg.paginate.page_count}</a>
            </li>
        </span>
    </ul>
  </div>
</div>


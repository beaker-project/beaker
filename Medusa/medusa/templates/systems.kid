<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Inventory</title>
</head>
<body>
    &nbsp;&nbsp;<b>${title}</b>
    <div py:if="num_items" class="list">
        <span py:for="page in tg.paginate.pages">
            <a py:if="page != tg.paginate.current_page"
                href="${tg.paginate.get_href(page)}">${page}</a>
            <b py:if="page == tg.paginate.current_page">${page}</b>
        </span>
        <a href="?tg_paginate_limit=${num_items}">all</a>
    </div>
    <table class="list">
        <tr class="list">
            <th class="list">
                <b>Name</b>
            </th>
            <th class="list">
                <b>Status</b>
            </th>
            <th class="list">
                <b>Vendor</b>
            </th>
            <th class="list">
                <b>Model</b>
            </th>
            <th class="list">
                <b>Serial Number</b>
            </th>
            <th class="list">
                <b>Location</b>
            </th>
            <th class="list">
                <b>Type</b>
            </th>
            <th class="list">
                <b>Contact</b>
            </th>
            <th class="list">
                <b>Last Update</b>
            </th>
        </tr>
        <?python row_color = "#FFFFFF" ?>
        <tr class="list" bgcolor="${row_color}" py:for="system in systems">
            <td class="list">
                <a class="list" href="${tg.url('./view/%s' % system.name)}">${system.name}</a>
            </td>
            <td class="list">
                ${system.status}
            </td>
            <td class="list" align="center">
                ${system.vendor}
            </td>
            <td class="list">
                ${system.model}
            </td>
            <td class="list">
                ${system.serial}
            </td>
            <td class="list">
                ${system.location}
            </td>
            <td class="list">
                ${system.type}
            </td>
            <td class="list">
                &nbsp;
            </td>
            <td class="list">
                ${system.date_lastcheckin}
            </td>
            <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
        </tr>
    </table>
    <a href="${tg.url('./new')}">Add ( + )</a>

</body>
</html>

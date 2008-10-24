<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>Activity</title>
</head>
<body>
    &nbsp;&nbsp;<b>${title}</b>
    <table class="list">
        <tr class="list">
            <th class="list">user_id</th>
            <th class="list">created</th>
            <th class="list">table_name</th>
            <th class="list">table_id</th>
            <th class="list">field_name</th>
            <th class="list">old_value</th>
            <th class="list">new_value</th>
        </tr>
        <?python row_color = "#FFFFFF" ?>
        <tr class="list" bgcolor="${row_color}" py:for="act in activity">
            <td class="list">${act.user_id}</td>
            <td class="list">${act.created}</td>
            <td class="list">${act.table_name}</td>
            <td class="list">${act.table_id}</td>
            <td class="list">${act.field_name}</td>
            <td class="list">${act.old_value}</td>
            <td class="list">${act.new_value}</td>
            <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
        </tr>
    </table>
</body>
</html>

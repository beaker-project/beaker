<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>${value_of('title', 'Form')}</title>
</head>

<body class="flora">

<div py:for="form in forms">
  <p py:content="form(method='POST', action=tg.url(form.action), value=value, options=options)">Form goes here</p>
</div>

<div>
 <table class="list">
  <tr class="list">
   <th class="list">
    <b>Key type</b>
   </th>
   <th class="list">
    <b>Key ID</b>
   </th>
   <th class="list">
    <b>&nbsp;</b>
   </th>
  </tr>
  <tr class="list" py:if="not ssh_keys">
   <td class="list" colspan="3">
    No SSH public keys stored.
   </td>
  </tr>
  <?python row_color = "#f1f1f1" ?>
  <tr class="list" bgcolor="${row_color}" py:for="key in ssh_keys">
   <td class="list">
    ${key.keytype}
   </td>
   <td class="list">
    ${key.ident}
   </td>
   <td class="list">
    <a class="button" href="${tg.url('/ssh_key_remove', id=key.id)}">Delete</a>
   </td>
   <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr>
 </table>
</div>

</body>
</html>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>${value_of('title', 'Form')}</title>
</head>

<body class="flora">

<h2>Preferences</h2>
<div>
  <p py:content="prefs_form(method='POST', action=tg.url(prefs_form.action), value=value, options=options)">Form goes here</p>
</div>

<h2>Root Password</h2>
  <p py:if="rootpw">The current default root password for provisioned systems is '<b>${rootpw}</b>'.</p>
  <p py:if="not rootpw">There is currently no default password configured.</p>

${rootpw_grid.display(rootpw_values)}

<h2>SSH Keys</h2>
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
    ${delete_link.display(dict(id=key.id), attrs=dict(class_='link'), 
        action=tg.url('ssh_key_remove'))}
   </td>
   <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr>
 </table>
</div>

<div>
  <p py:content="ssh_key_form(method='POST', action=tg.url(ssh_key_form.action), value=value, options=options)">Form goes here</p>
</div>

<h2>Submission delegates</h2>
<div>
 ${submission_delegates_grid.display(value.submission_delegates)}
 <div py:content="submission_delegate_form(method='POST',
       action=tg.url('add_submission_delegate'), value=value)">
 </div>
</div>
</body>
</html>

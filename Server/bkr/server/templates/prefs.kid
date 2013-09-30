<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>User Preferences</title>
</head>

<body>
<div class="page-header">
  <h1>User Preferences</h1>
</div>

  <p py:content="prefs_form(method='POST', action=tg.url(prefs_form.action), value=value, options=options)">Form goes here</p>

<h2>Root Password</h2>
  <p py:if="rootpw">The current default root password for provisioned systems is '<b>${rootpw}</b>'.</p>
  <p py:if="not rootpw">There is currently no default password configured.</p>

${rootpw_grid.display(rootpw_values)}

<h2>SSH Keys</h2>
<table class="table table-striped">
  <thead>
    <tr><th>Key type</th><th>Key ID</th><th></th></tr>
  </thead>
  <tbody>
    <tr py:for="key in ssh_keys">
      <td>${key.keytype}</td>
      <td>${key.ident}</td>
      <td>
        ${delete_link.display(dict(id=key.id), action=tg.url('ssh_key_remove'))}
      </td>
    </tr>
  </tbody>
  <tfoot py:if="not ssh_keys">
    <tr>
      <td colspan="3">No SSH public keys stored.</td>
    </tr>
  </tfoot>
</table>

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

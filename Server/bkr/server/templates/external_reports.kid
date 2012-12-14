<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<title>${title}</title>
<link rel="stylesheet" type="text/css" href="${tg.url('/static/css/external_report.css')}" />
</head>
<body>
<h2>$title</h2>
<div xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
  <div py:for="report in value" class='external-report'>
    <h3>${report.name}</h3>
    <span class='url'>URL:</span> <a href="${report.url}">${report.url}</a>
    <h5>Description:</h5>
    <p py:if="report.description">${report.description}</p>
    <p py:if="not report.description" py:strip='1' >No Description</p>
    <span py:if="'admin' in tg.identity.groups" py:strip='1'>
      <a href="${tg.url('edit', tgparams=dict(id=report.id))}">Edit</a>
      ${delete_link.display(dict(id=report.id), attrs=dict(class_='link'),
        action=tg.url('delete'))}
    </span>
  </div>
  <div py:if="'admin' in tg.identity.groups" class='offset'>
    <a href="${action}">Add Report ( + )</a>
  </div>
</div>
</body>
</html>

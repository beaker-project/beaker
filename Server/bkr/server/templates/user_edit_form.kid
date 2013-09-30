<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>${title}</title>
</head>
<body>
<div class="page-header">
  <h1>${title}</h1>
</div>
    <div py:if="form">
<p py:content="form(method='GET', action=tg.url(action), value=value, options=options)">Form goes here</p>
    </div>
    <div py:if="groupsgrid is not None">
        <h2>Group membership</h2>
        ${groupsgrid.display(value.groups, name='groups_grid')}
    </div>
</body>
</html>

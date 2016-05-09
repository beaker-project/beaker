<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>$title</title>
</head>
<body class="with-localised-datetimes">
<div class="page-header">
  <h1>$title</h1>
</div>
<span py:if="search_bar">${search_bar.display(method='GET', action=tg.url(action), value=searchvalue, options=options)}</span>
<div py:if="warn_msg" class="alert alert-error">${warn_msg}</div>
${grid.display(list)}
</body>
</html>

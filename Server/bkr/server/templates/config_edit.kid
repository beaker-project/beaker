<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>${title}</title>
</head>

<body class="with-localised-datetimes">
  <div class="page-header">
    <h1>${title} <small>${subtitle}</small></h1>
  </div>
  <div py:if="warn_msg" class="alert alert-warn">${warn_msg}</div>

  ${grid.display(list)}

  <div py:if="form">
    <h2>Update setting</h2>
    <p py:content="form(method='GET', action=tg.url(action), value=value, options=options)">Form goes here</p>
  </div>


</body>
</html>

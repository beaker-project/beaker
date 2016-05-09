<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>${value_of('title', 'Form')}</title>
</head>


<body class="with-localised-datetimes">
  <div class="page-header">
    <h1>${value_of('title', 'Form')}</h1>
  </div>
    <div py:if="form">
<p py:content="form(method='POST', action=action, value=value, options=options)">Form goes here</p>
    </div>
</body>
</html>

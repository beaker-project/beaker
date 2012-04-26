<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>${value_of('title', 'Form')}</title>
</head>

<body class="flora">
  <div py:if="warn_msg" class="msg warn" style='text-align:center'>${warn_msg}</div>
  <h2>${title}</h2>

  ${grid.display(list)}

  <div py:if="form">
    <p py:content="form(method='GET', action=tg.url(action), value=value, options=options)">Form goes here</p>
  </div>


</body>
</html>

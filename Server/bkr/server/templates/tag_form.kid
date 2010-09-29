<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Tag Edit</title>
</head>
<body class="flora">
    <div py:if="form">
<p py:content="form(method='GET', action=action, value=value, options=options, disabled_fields=disabled_fields)">Form goes here</p>
    </div>
</body>
</html>

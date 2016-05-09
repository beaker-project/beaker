<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<title>${title}</title>
</head>
<body class="with-localised-datetimes">
<div class="page-header">
  <h1>${title}</h1>
</div>
<div py:if="widget">${widget.display(value=value, options=widget_options, attrs=widget_attrs)} </div>


</body>
</html>

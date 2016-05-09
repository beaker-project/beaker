<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<script type='text/javascript' src="${tg.url('/static/javascript/util.js')}" />
<title>$title</title>
</head>
<body class="with-localised-datetimes">
<div class="page-header">
  <h1>$title</h1>
</div>
${search_widget.display()} 
${alpha_nav_bar.display()}
${grid.display(list)}
</body>
</html>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<script type='text/javascript' src="${tg.url('/static/javascript/util.js')}" />
<script type='text/javascript' src="${tg.url('/static/javascript/jquery-ui-1.9.2.min.js')}" />
<link rel="stylesheet" type="text/css" href="${tg.url('/static/css/smoothness/jquery-ui.css')}" />
<title>$title</title>
</head>
<body>
<h2>$title</h2>
<span>
${search_widget.display()} 
</span>
${alpha_nav_bar.display()}
${grid.display(list)}

<a py:if="addable is not False" href="${tg.url('./new')}">Add ( + )</a>
</body>
</html>

<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>$title</title>
<link py:if="defined('atom_url')" rel="feed" title="Atom feed" href="${atom_url}" />
</head>
<body class="with-localised-datetimes">
<div class="page-header">
  <h1>$title</h1>
</div>
<span py:if="search_bar">${search_bar.display(method='GET', action=action, value=searchvalue, options=options)}</span>
<span py:if="defined('search_widget')" py:content="search_widget.display()" />
${grid.display(list)}
</body>
</html>

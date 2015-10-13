<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>$title</title>
<link py:if="defined('atom_url')" rel="feed" title="Atom feed" href="${atom_url}" />
</head>
<body>
<div class="page-header">
  <h1>$title</h1>
</div>
<script type="text/javascript">
var collection = new ${grid_collection_type}(
        ${tg.to_json(grid_collection_data)},
        {parse: true, url: ${tg.to_json(grid_collection_url)}});
collection.on('request', function (model_or_collection, xhr, options) {
    // 'request' is also triggered on the collection when a model *inside* the 
    // collection makes a request, but we don't care about that here, so ignore
    if (model_or_collection != collection)
        return;
    // update the address bar to match the new grid state
    window.history.replaceState(undefined, undefined, '?' + $.param(options.data));
});
$(function () {
    new ${grid_view_type}({
        model: collection,
        el: $('#grid'),
        add_label: ${tg.to_json(value_of('grid_add_label', None))},
        add_view_type: ${value_of('grid_add_view_type', 'null')},
        add_view_options: ${tg.to_json(value_of('grid_add_view_options', dict()))},
    });
});
</script>
<div id="grid"></div>
</body>
</html>

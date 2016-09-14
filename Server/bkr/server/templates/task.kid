<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Task ${attributes['name']}</title>
</head>

<body class="with-localised-datetimes">
    <div id="task-view"></div>

    <script type="text/javascript">
        var task = new Task(${tg.to_json(attributes)}, {parse: true, url: ${tg.to_json(tg.url(url))}});
        $(function() {
            new TaskView({model: task, el: $('#task-view')});
        });
    </script>
<div>
<h2>Executed Tasks</h2>
    ${form.display(
    value=value,
    options=options,
    hidden=options['hidden'],
    action=action,
    target_dom='task_items',
    update='task_items',
    )}
    <div id="task_items">&nbsp;</div>
 </div>
</body>
</html>

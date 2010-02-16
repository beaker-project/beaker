<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1
-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Executed Tasks</title>
</head>
<body class="flora">
<h2>Executed Tasks</h2>
    ${form.display(
    value=value,
    options=options,
    hidden=hidden,
    action=action,
    target_dom='task_items',
    update='task_items',
    )}
    <div id="task_items">${task_widget(tasks=tasks, hidden=hidden)}</div>
</body>
</html>

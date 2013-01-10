<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Task ${task.name}</title>
</head>

<body class="flora">
<table width="97%">
    <tr>
        <td>
            <div class="show"><a href="${tg.url('/tasks')}">Tasks</a> - ${task.name}</div>
        </td>
    </tr>
</table>
<table class="show">
    <tr py:if="task.description">
        <td class="title"><b>Description:</b></td>
        <td class="value">${task.description}</td>
    </tr>
    <tr py:if="task.valid">
        <td class="title"><b>Valid:</b></td>
        <td class="value">${task.valid}</td>
    </tr>
    <tr py:if="task.path">
        <td class="title"><b>Path:</b></td>
        <td class="value">${task.path}</td>
    </tr>
    <tr>
        <td class="title"><b>Expected Time:</b></td>
        <td class="value">${task.elapsed_time()}</td>
    </tr>
    <tr py:if="task.creation_date">
        <td class="title"><b>Creation Date:</b></td>
        <td class="value"><span class="datetime">${task.creation_date}</span></td>
    </tr>
    <tr py:if="task.update_date">
        <td class="title"><b>Updated Date:</b></td>
        <td class="value"><span class="datetime">${task.update_date}</span></td>
    </tr>
    <tr py:if="task.owner">
        <td class="title"><b>Owner:</b></td>
        <td class="value">${task.owner}</td>
    </tr>
    <tr py:if="task.uploader">
        <td class="title"><b>Uploader:</b></td>
        <td class="value">${task.uploader.email_link}</td>
    </tr>
    <tr py:if="task.version">
        <td class="title"><b>Version:</b></td>
        <td class="value">${task.version}</td>
    </tr>
    <tr py:if="task.license">
        <td class="title"><b>License:</b></td>
        <td class="value">${task.license}</td>
    </tr>
    <tr py:if="task.rpm">
        <td class="title"><b>RPM:</b></td>
        <td class="value"><a href="/rpms/${task.rpm}">${task.rpm}</a></td>
    </tr>
    <tr py:if="task.needs">
        <td class="title"><b>Needs:</b></td>
        <td class="value">
            <span py:for="need in task.needs">${need.property}<br/></span>
        </td>
    </tr>
    <tr py:if="task.bugzillas">
        <td class="title"><b>Bugzillas:</b></td>
        <td class="value">
            <span py:for="bug in task.bugzillas">
                <a href="https://bugzilla.redhat.com/show_bug.cgi?id=${bug.bugzilla_id}">${bug.bugzilla_id}</a>
                <br/>
            </span>
        </td>
    </tr>
    <tr py:if="task.types">
        <td class="title"><b>Types:</b></td>
        <td class="value">
            <span py:for="type in task.types">${type.type}<br/></span>
        </td>
    </tr>
    <tr py:if="task.runfor">
        <td class="title"><b>Run For:</b></td>
        <td class="value">
            <span py:for="package in task.runfor">
                ${package}
                <br/>
            </span>
        </td>
    </tr>
    <tr py:if="task.priority">
        <td class="title"><b>Priority:</b></td>
        <td class="value">${task.priority}</td>
    </tr>
    <tr py:if="task.destructive is not None">
        <td class="title"><b>Destructive:</b></td>
        <td class="value">${task.destructive}</td>
    </tr>
    <tr py:if="task.required">
        <td class="title"><b>Requires:</b></td>
        <td class="value">
            <span py:for="package in task.required">${package}<br/></span>
        </td>
    </tr>
    <tr py:if="task.excluded_osmajor">
        <td class="title"><b>Excluded OSMajors:</b></td>
        <td class="value">
            <span py:for="osmajor in task.excluded_osmajor">${osmajor.osmajor}<br/></span>
        </td>
    </tr>
    <tr py:if="task.excluded_arch">
        <td class="title"><b>Excluded Arches:</b></td>
        <td class="value">
            <span py:for="arch in task.excluded_arch">${arch.arch}<br/></span>
        </td>
    </tr>
</table>
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

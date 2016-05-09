<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Task ${task.name}</title>
</head>

<body class="with-localised-datetimes">
<div class="page-header">
  <h1>Task ${task.name}</h1>
</div>
<table class="table table-bordered">
  <tbody>
    <tr py:if="task.description">
        <th>Description</th>
        <td>${task.description}</td>
    </tr>
    <tr py:if="task.valid">
        <th>Valid</th>
        <td>${task.valid}</td>
    </tr>
    <tr py:if="task.path">
        <th>Path</th>
        <td>${task.path}</td>
    </tr>
    <tr>
        <th>Expected Time</th>
        <td>${task.elapsed_time()}</td>
    </tr>
    <tr py:if="task.creation_date">
        <th>Creation Date</th>
        <td><span class="datetime">${task.creation_date}</span></td>
    </tr>
    <tr py:if="task.update_date">
        <th>Updated Date</th>
        <td><span class="datetime">${task.update_date}</span></td>
    </tr>
    <tr py:if="task.owner">
        <th>Owner</th>
        <td>${task.owner}</td>
    </tr>
    <tr py:if="task.uploader">
        <th>Uploader</th>
        <td>${task.uploader.email_link}</td>
    </tr>
    <tr py:if="task.version">
        <th>Version</th>
        <td>${task.version}</td>
    </tr>
    <tr py:if="task.license">
        <th>License</th>
        <td>${task.license}</td>
    </tr>
    <tr py:if="task.rpm">
        <th>RPM</th>
        <td><a href="/rpms/${task.rpm}">${task.rpm}</a></td>
    </tr>
    <tr py:if="task.needs">
        <th>Needs</th>
        <td>
          <ul class="unstyled">
            <li py:for="need in task.needs">${need.property}</li>
          </ul>
        </td>
    </tr>
    <tr py:if="task.bugzillas">
        <th>Bugzillas</th>
        <td>
          <ul class="unstyled">
            <li py:for="bug in task.bugzillas">
                <a href="https://bugzilla.redhat.com/show_bug.cgi?id=${bug.bugzilla_id}">${bug.bugzilla_id}</a>
            </li>
          </ul>
        </td>
    </tr>
    <tr py:if="task.types">
        <th>Types</th>
        <td>
          <ul class="unstyled">
            <li py:for="type in task.types">${type.type}</li>
          </ul>
        </td>
    </tr>
    <tr py:if="task.runfor">
        <th>Run For</th>
        <td>
          <ul class="unstyled">
            <li py:for="package in task.runfor">
                ${package}
            </li>
          </ul>
        </td>
    </tr>
    <tr py:if="task.priority">
        <th>Priority</th>
        <td>${task.priority}</td>
    </tr>
    <tr py:if="task.destructive is not None">
        <th>Destructive</th>
        <td>${task.destructive}</td>
    </tr>
    <tr py:if="task.required">
        <th>Requires</th>
        <td>
          <ul class="unstyled">
            <li py:for="package in task.required">${package}</li>
          </ul>
        </td>
    </tr>
    <tr py:if="task.excluded_osmajor">
        <th>Excluded OSMajors</th>
        <td>
          <ul class="unstyled">
            <li py:for="osmajor in task.excluded_osmajor">${osmajor.osmajor}</li>
          </ul>
        </td>
    </tr>
    <tr py:if="task.excluded_arch">
        <th>Excluded Arches</th>
        <td>
          <ul class="unstyled">
            <li py:for="arch in task.excluded_arch">${arch.arch}</li>
          </ul>
        </td>
    </tr>
  </tbody>
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

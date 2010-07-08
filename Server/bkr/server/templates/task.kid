<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Task ${task.name}</title>
</head>

<?python
from cgi import escape

runfor = ''
required = ''
needs = ''
bugzillas = ''
types = ''
excluded_osmajors = '<br/>'.join(['%s' % osmajor.osmajor for osmajor in task.excluded_osmajor])
excluded_arches  = '<br/>'.join(['%s' % arch.arch for arch in task.excluded_arch])

for need in task.needs:
    needs += '%s<br/>' % need.property
needs = needs.replace('&', '&amp;')

for package in task.runfor:
    runfor += '<a href="/package/%s">%s</a><br/>' % (package,package)
runfor = runfor.replace('&', '&amp;')

for bug in task.bugzillas:
    bugzillas += '<a href="http://bugzilla.redhat.com/show_bug.cgi?id=%s">%s</a><br/>' % (bug.bugzilla_id,bug.bugzilla_id)
bugzillas = bugzillas.replace('&', '&amp;')

for package in task.required:
    required += '%s<br/>' % package
required = required.replace('&', '&amp;')

for type in task.types:
    types += '%s<br/>' % type.type
types = types.replace('&', '&amp;')
?>

<body class="flora">
<table width="97%">
    <tr>
        <td>
            <div class="show"><a href="${tg.url('/tasks')}">Tasks</a> - ${task.name}</div>
        </td>
    </tr>
</table>
<table class="show">
    <tr py:for="field in (
        ['Description',       task.description],
        ['Path',              task.path],
        ['Expected Time',     task.elapsed_time()],
        ['Creation Date',     task.creation_date],
        ['Updated Date',      task.update_date],
        ['Version',           task.version],
        ['License',           task.license],
        ['RPM',               task.rpm],
        ['Needs',             (needs) and XML(needs) or ''],
        ['Bugzillas',         (bugzillas) and XML(bugzillas) or ''],
        ['Types',             (types) and XML(types) or ''],
        ['Run For',           (runfor) and XML(runfor) or ''],
        ['Requires',          (required) and XML(required) or ''],
        ['Excluded OSMajors', (excluded_osmajors) and XML(excluded_osmajors) or ''],
        ['Excluded Arches',   (excluded_arches) and XML(excluded_arches) or ''],
    )">
        <span py:if="field[1] != None and field[1] != ''">
            <td class="title"><b>${field[0]}:</b></td>
            <td class="value">${field[1]}</td>
        </span>
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

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Test ${task.name}</title>
</head>

<?python
from cgi import escape

runfor = ''
required = ''
needs = ''
bugzillas = ''
types = ''

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
            <div class="show"><a href="${tg.url('/tasks')}">Tests</a> - ${task.name}</div>
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
    )">
        <span py:if="field[1] != None and field[1] != ''">
            <td class="title"><b>${field[0]}:</b></td>
            <td class="value">${field[1]}</td>
        </span>
    </tr>
</table>
<table width="97%" class="list" py:if="task.runs">
    <tr class="list">
        <td colspan="7" class="list">
            <div class="show">Last 10 Test Runs for this Test</div>
        </td>
    </tr>
    <tr class="list">
     <th class="list">Run ID</th>
     <th class="list">Distro</th>
     <th class="list">Family</th>
     <th class="list">Arch</th>
     <th class="list">System</th>
     <th class="list">Status</th>
     <th class="list">Result</th>
     <th class="list">Duration</th>
    </tr>
    <tr class="list" py:for="taskrun in reversed(task.runs[-10:])">
      <td class="list">${taskrun.id}</td>
      <td class="list"><span py:if="taskrun.recipe.distro">${taskrun.recipe.distro.name}</span></td>
      <td class="list"><span py:if="taskrun.recipe.distro">${taskrun.recipe.distro.osversion}</span></td>
      <td class="list"><span py:if="taskrun.recipe.distro">${taskrun.recipe.distro.arch}</span></td>
      <td class="list">${taskrun.recipe.system}</td>
      <td class="list">${taskrun.status}</td>
      <td class="list">${taskrun.duration}</td>
    </tr>
</table>
</body>
</html>

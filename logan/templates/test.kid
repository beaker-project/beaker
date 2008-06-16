<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Test ${test.name}</title>
</head>

<?python
from cgi import escape

runfor = ''
required = ''
arch_include = ''
family_include = ''
family_exclude = ''
needs = ''
bugzillas = ''
types = ''

for need in test.needs:
    needs += '%s<br/>' % need.property
needs = needs.replace('&', '&amp;')

for arch in test.arches:
    arch_include += '%s<br/>' % arch.arch
arch_include = arch_include.replace('&', '&amp;')

for family in test.families:
    if test.family_list == 1:
        family_include += '%s<br/>' % family.name
    else:
        family_exclude += '%s<br/>' % family.name
family_include = family_include.replace('&', '&amp;')
family_exclude = family_exclude.replace('&', '&amp;')

for package in test.runfor:
    runfor += '<a href="/package/%s">%s</a><br/>' % (package,package)
runfor = runfor.replace('&', '&amp;')

for bug in test.bugzillas:
    bugzillas += '<a href="http://bugzilla.redhat.com/show_bug.cgi?id=%s">%s</a><br/>' % (bug.bugzilla_id,bug.bugzilla_id)
bugzillas = bugzillas.replace('&', '&amp;')

for package in test.required:
    required += '%s<br/>' % package
required = required.replace('&', '&amp;')

for type in test.types:
    types += '%s<br/>' % type.type
types = types.replace('&', '&amp;')
?>

<body class="flora">
<table width="97%">
    <tr>
        <td>
            <div class="show"><a href="${tg.url('/tests')}">Tests</a> - ${test.name}</div>
        </td>
    </tr>
</table>
<table class="show">
    <tr py:for="field in (
        ['Description',       test.description],
        ['Path',              test.path],
        ['Expected Time',     test.elapsed_time()],
        ['Creation Date',     test.creation_date],
        ['Updated Date',      test.update_date],
        ['Version',           test.version],
        ['License',           test.license],
        ['RPM',               test.rpm],
        ['Arches Included',   (arch_include) and XML(arch_include) or ''],
        ['Families Included', (family_include) and XML(family_include) or ''],
        ['Families Excluded', (family_exclude) and XML(family_exclude) or ''],
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
<table width="97%" py:if="test.runs">
    <tr>
        <td>
            <div class="show">Last 10 Test Runs for this Test</div>
        </td>
    </tr>
    <tr py:for="testrun in test.runs[-10:]">
      <td>${testrun}</td>
    </tr>
</table>
</body>
</html>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>${title} ${value.id}: ${value}</title>
    <script src="${tg.url('/static/javascript/magic_forms.js')}" type='text/javascript'/>
    <style type="text/css">
        table.lab_controllers tbody tr {
            border: none;
        }
        table.lab_controllers tbody tr:last-child {
            border-bottom: 1px solid #bcbcbc !important;
        }
        table.lab_controllers td {
            padding: 5px 25px;
        }
    </style>
</head>
<body class="flora">

<h2>Distro Tree</h2>
<table class="list">
    <tbody>
        <tr class="list">
            <th class="list" style="width: 25%;">ID</th>
            <td class="list">${value.id}</td>
        </tr>
        <tr class="list">
            <th class="list">Distro</th>
            <td class="list">${value.distro.link}</td>
        </tr>
        <tr class="list">
            <th class="list">Variant</th>
            <td class="list">${value.variant}</td>
        </tr>
        <tr class="list">
            <th class="list">Arch</th>
            <td class="list">${value.arch}</td>
        </tr>
        <tr class="list">
            <th class="list">Date Created</th>
            <td class="list datetime">${value.date_created}</td>
        </tr>
    </tbody>
</table>

<div class="tabber">

<div class="tabbertab">
<h2>Lab Controllers</h2>
<table class="list lab_controllers">
    <thead>
        <tr class="list">
            <th class="list">Lab Controller</th>
            <th class="list">URL</th>
            <th class="list"></th>
        </tr>
    </thead>
    <?python i = 0 ?>
    <tbody py:for="lab_controller in lab_controllers" py:if="lab_controller_assocs[lab_controller]">
        <tr py:for="j, lca in enumerate(lab_controller_assocs[lab_controller])"
            class="list ${i%2 and 'odd' or 'even'}">
            <td class="list" py:if="j == 0" rowspan="${len(lab_controller_assocs[lab_controller])}">${lab_controller}</td>
            <td class="list">
                <a class="list" href="${lca.url}"
                 py:strip="lca.url.startswith('nfs://') or lca.url.startswith('file://')">
                    ${lca.url}
                </a>
            </td>
            <td class="list">
             <span py:if='not readonly' py:strip='1'>
              ${delete_link.display(dict(id=lca.id), attrs=dict(class_='link'),
                  action=tg.url('./lab_controller_remove'))}
             </span>
            </td>
        </tr>
        <?python i += 1 ?>
    </tbody>
    <tbody py:if="not readonly">
        <tr class="list ${i%2 and 'odd' or 'even'}">
            <td class="list">
                <select id="lab_controller_id">
                    <option py:for="lab_controller in lab_controllers"
                            value="${lab_controller.id}">${lab_controller}</option>
                </select>
            </td>
            <td class="list">
                <input id="url" type="text" size="100" maxlength="255"/>
            </td>
            <td class="list">

            <form action="lab_controller_add" method="post" name="lab_controller_add_form">
                <input type="hidden" name="distro_tree_id" value="${value.id}" />
                <input type="hidden" id="url_hidden" name="url" />
                <input type="hidden" id="lab_controller_id_hidden" name="lab_controller_id" />
                <a onclick="populate_form_elements(this.parentNode);return true" href="javascript:document.lab_controller_add_form.submit()">Add ( + )</a>
                </form>
            </td>
        </tr>
    </tbody>
</table>
</div>

<div class="tabbertab">
<h2>Install Options</h2>
${install_options_widget.display(value, readonly=readonly)}
</div>

<div class="tabbertab">
<h2>Repos</h2>
<table class="list">
    <thead>
        <tr class="list">
            <th class="list">Repo ID</th>
            <th class="list">Type</th>
            <th class="list" style="width: 70%;">Path</th>
        </tr>
    </thead>
    <tbody>
        <tr py:for="i, repo in enumerate(value.repos)" class="list ${i%2 and 'odd' or 'even'}">
            <td class="list">${repo.repo_id}</td>
            <td class="list">${repo.repo_type}</td>
            <td class="list">${repo.path}</td>
        </tr>
    </tbody>
</table>

<h3 style="display: block;">Download Yum Config</h3>
<table class="list yum_config">
    <thead>
        <tr class="list">
            <th class="list">Lab Controller</th>
            <th class="list" style="width: 70%;">Yum Config</th>
        </tr>
    </thead>
    <tbody>
        <?python i = 0 ?>
        <tr py:for="lab_controller in lab_controllers"
            py:if="lab_controller_assocs[lab_controller]"
            class="list ${i%2 and 'odd' or 'even'}">
            <td class="list">${lab_controller}</td>
            <td class="list">
                <?python filename = '%s.repo' % unicode(value).replace(' ', '-') ?>
                <a href="yum_config/${value.id}/${filename}?lab=${lab_controller.fqdn}">${filename}</a>
            </td>
            <?python i += 1 ?>
        </tr>
    </tbody>
</table>
</div>

<div class="tabbertab">
<h2>Images</h2>
<table class="list">
    <thead>
        <tr class="list">
            <th class="list">Image Type</th>
            <th class="list">Kernel Type</th>
            <th class="list" style="width: 70%;">Path</th>
        </tr>
    </thead>
    <tbody>
        <tr py:for="i, image in enumerate(value.images)" class="list ${i%2 and 'odd' or 'even'}">
            <td class="list">${image.image_type}</td>
            <td class="list">${image.kernel_type}</td>
            <td class="list">${image.path}</td>
        </tr>
    </tbody>
</table>
</div>

<div class="tabbertab">
<h2>Executed Tasks</h2>
${form_task.display(value=dict(distro_tree_id=value.id),
        target_dom='task_items',
        update='task_items')}
<div id="task_items" />
</div>

</div>

</body>
</html>

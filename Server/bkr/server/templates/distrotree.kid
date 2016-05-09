<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>${value}</title>
    <script src="${tg.url('/static/javascript/magic_forms.js')}" type='text/javascript'/>
</head>
<body class="with-localised-datetimes">
<div class="page-header">
  <h1>${value}</h1>
</div>

<table class="table table-bordered" style="max-width: 30em;">
    <tbody>
        <tr>
            <th>ID</th>
            <td>${value.id}</td>
        </tr>
        <tr>
            <th>Distro</th>
            <td>${value.distro.link}</td>
        </tr>
        <tr>
            <th>Variant</th>
            <td>${value.variant}</td>
        </tr>
        <tr>
            <th>Arch</th>
            <td>${value.arch}</td>
        </tr>
        <tr>
            <th>Date Created</th>
            <td class="datetime">${value.date_created}</td>
        </tr>
    </tbody>
</table>

<ul class="nav nav-tabs">
  <li><a data-toggle="tab" href="#lab-controllers">Lab Controllers</a></li>
  <li><a data-toggle="tab" href="#install-options">Install Options</a></li>
  <li><a data-toggle="tab" href="#repos">Repos</a></li>
  <li><a data-toggle="tab" href="#images">Images</a></li>
  <li><a data-toggle="tab" href="#executed-tasks">Executed Tasks</a></li>
</ul>

<div class="tab-content">

<div class="tab-pane" id="lab-controllers">
<table class="table table-one-line-per-row">
    <thead>
        <tr>
            <th>Lab Controller</th>
            <th>URL</th>
            <th></th>
        </tr>
    </thead>
    <tbody>
      <span py:for="lab_controller in lab_controllers" py:if="lab_controller_assocs[lab_controller]" py:strip="True">
        <tr py:for="j, lca in enumerate(lab_controller_assocs[lab_controller])">
            <td py:if="j == 0" rowspan="${len(lab_controller_assocs[lab_controller])}">${lab_controller}</td>
            <td>
                <a href="${lca.url}"
                 py:strip="lca.url.startswith('nfs://') or lca.url.startswith('file://')">
                    ${lca.url}
                </a>
            </td>
            <td>
             <span py:if='not readonly' py:strip='1'>
              ${delete_link.display(dict(id=lca.id), action=tg.url('./lab_controller_remove'))}
             </span>
            </td>
        </tr>
      </span>
    </tbody>
    <tfoot py:if="not readonly">
        <tr>
            <td>
                <select id="lab_controller_id">
                    <option py:for="lab_controller in lab_controllers"
                            value="${lab_controller.id}">${lab_controller}</option>
                </select>
            </td>
            <td>
                <input id="url" type="text" size="100" maxlength="255"/>
            </td>
            <td>

            <form action="lab_controller_add" method="post" name="lab_controller_add_form" onsubmit="populate_form_elements(this);">
                <input type="hidden" name="distro_tree_id" value="${value.id}" />
                <input type="hidden" id="url_hidden" name="url" />
                <input type="hidden" id="lab_controller_id_hidden" name="lab_controller_id" />
                <button class="btn btn-primary" type="submit"><i class="fa fa-plus"/> Add</button>
                </form>
            </td>
        </tr>
    </tfoot>
</table>
</div>

<div class="tab-pane" id="install-options">
${install_options_widget.display(value, readonly=readonly)}
</div>

<div class="tab-pane" id="repos">
<table class="table table-one-line-per-row table-striped">
    <thead>
        <tr>
            <th>Repo ID</th>
            <th>Type</th>
            <th style="width: 70%;">Path</th>
        </tr>
    </thead>
    <tbody>
        <tr py:for="repo in value.repos">
            <td>${repo.repo_id}</td>
            <td>${repo.repo_type}</td>
            <td>${repo.path}</td>
        </tr>
    </tbody>
</table>

<h3>Download Yum Config</h3>
<table class="yum_config table table-one-line-per-row table-striped">
    <thead>
        <tr>
            <th>Lab Controller</th>
            <th style="width: 70%;">Yum Config</th>
        </tr>
    </thead>
    <tbody>
        <tr py:for="lab_controller in lab_controllers"
            py:if="lab_controller_assocs[lab_controller]">
            <td>${lab_controller}</td>
            <td>
                <?python filename = '%s.repo' % unicode(value).replace(' ', '-') ?>
                <a href="yum_config/${value.id}/${filename}?lab=${lab_controller.fqdn}">${filename}</a>
            </td>
        </tr>
    </tbody>
</table>
</div>

<div class="tab-pane" id="images">
<table class="table table-one-line-per-row table-striped">
    <thead>
        <tr>
            <th>Image Type</th>
            <th>Kernel Type</th>
            <th style="width: 70%;">Path</th>
        </tr>
    </thead>
    <tbody>
        <tr py:for="image in value.images">
            <td>${image.image_type}</td>
            <td>${image.kernel_type}</td>
            <td>${image.path}</td>
        </tr>
    </tbody>
</table>
</div>

<div class="tab-pane" id="executed-tasks">
${form_task.display(value=dict(distro_tree_id=value.id),
        target_dom='task_items',
        update='task_items')}
<div id="task_items" />
</div>

</div>

<script type="text/javascript">
    $(function () { link_tabs_to_anchor('beaker_distrotree_tabs', '.nav-tabs'); });
</script>
</body>
</html>

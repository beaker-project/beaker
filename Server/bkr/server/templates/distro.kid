<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

 <head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
  <title>${value.name}</title>
 </head>


<body class="with-localised-datetimes">
<div class="page-header">
  <h1>${value.name}</h1>
</div>

<table class="table table-bordered">
  <tbody>
    <tr>
      <th>ID</th>
      <td>${value.id}</td>
    </tr>
    <tr>
      <th>Date Created</th>
      <td class="datetime">${value.date_created}</td>
    </tr>
    <tr>
      <th>OS Version</th>
      <td>${value.osversion}</td>
    </tr>
  </tbody>
</table>

<h2>Distro Trees</h2>
<table class="table table-striped table-hover">
  <thead>
    <tr>
      <th>ID</th><th>Variant</th><th>Arch</th><th>Provision</th>
    </tr>
  </thead>
  <tbody>
    <tr py:for="tree in value.trees">
      <td><a href="${tg.url('/distrotrees/%s' % tree.id)}">${tree.id}</a></td>
      <td>${tree.variant}</td>
      <td>${tree.arch}</td>
      <td>
        <div py:if="tree.lab_controller_assocs" class="btn-group">
          <a class="btn" href="${tg.url('/reserveworkflow/', distro_tree_id=tree.id)}">Provision</a>
        </div>
      </td>
    </tr>
  </tbody>
</table>

  <div class="tags"><h2>Tags</h2>
   ${form.display(method='get', action=action, value=value, options=options)}
  </div>
  <div><h2>Executed Tasks</h2>
    ${form_task.display(
    value=value_task,
    options=options,
    action=action_task,
    target_dom='task_items',
    update='task_items',
    )}
    <div id="task_items">&nbsp;</div>
  </div>
 </body>
</html>

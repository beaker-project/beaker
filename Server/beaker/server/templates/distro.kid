<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

 <head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
  <title>${title}</title>
 </head>


 <body class="flora">
  <h2>Distro</h2>
  <table class="list">
   <tr class="list">
    <th class="list">
      <b>Install Name</b>
    </th>
    <td class="list" colspan="3">
     ${value.install_name}
    </td>
   </tr>
   <tr class="list">
    <th class="list">
      <b>Name</b>
    </th>
    <td class="list" colspan="3">
     ${value.name}
    </td>
   </tr>
   <tr class="list">
    <th class="list">
      <b>Date Created</b>
    </th>
    <td class="list" colspan="3">
     ${value.date_created}
    </td>
   </tr>
   <tr class="list">
    <th class="list">
      <b>Arch</b>
    </th>
    <td class="list" colspan="3">
     ${value.arch}
    </td>
   </tr>
   <tr class="list">
    <th class="list">
      <b>Breed</b>
    </th>
    <td class="list" colspan="3">
     ${value.breed}
    </td>
   </tr>
   <tr class="list">
    <th class="list">
      <b>OS Version</b>
    </th>
    <td class="list" colspan="3">
     ${value.osversion}
    </td>
   </tr>
   <tr class="list">
    <th class="list">
      <b>Variant</b>
    </th>
    <td class="list" colspan="3">
     ${value.variant}
    </td>
   </tr>
   <tr class="list">
    <th class="list">
      <b>Virt</b>
    </th>
    <td class="list" colspan="3">
     ${value.virt}
    </td>
   </tr>
  </table>

  <div><h2>Lab Controllers</h2>
   <table class="list">
    <tr py:for="labcontroller in value.lab_controller_assocs" class="list">
     <th class="list">${labcontroller.lab_controller.fqdn}</th>
     <td class="list">${labcontroller.tree_path}</td>
    </tr>
   </table>
  </div>
  <div><h2>Tags</h2>
   ${form.display(method='get', action=action, value=value, options=options)}
  </div>
  <div><h2>Executed Tasks</h2>
    ${form_task.display(
    value=value_task,
    options=options,
    hidden=options['hidden'],
    action=action_task,
    target_dom='task_items',
    update='task_items',
    before='getElement(\'loading\').innerHTML=\'Searching...\';',
    on_complete='getElement(\'loading\').innerHTML=\'Done!\';',
    )}
    <div id="loading"></div>
    <div id="task_items">&nbsp;</div>
  </div>
 </body>
</html>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>${title}</title>
</head>
<body>
    <p py:content="system_form(method='GET', action=action, value=value, options=options)">
Form goes here</p>
    <div py:if="system" class="tabber">
     <div class="tabbertab"><h2>Details</h2>
      <span py:if="system.cpu">
       &nbsp;&nbsp;<b>Cpu</b>
       <table class="list">
        <tr class="list">
            <th class="list">
                <b>Vendor</b>
            </th>
            <th class="list">
                <b>Model Name</b>
            </th>
            <th class="list">
                <b>Model</b>
            </th>
            <th class="list">
                <b>Family</b>
            </th>
            <th class="list">
                <b>Stepping</b>
            </th>
            <th class="list">
                <b>Speed</b>
            </th>
            <th class="list">
                <b>Processors</b>
            </th>
            <th class="list">
                <b>Cores</b>
            </th>
            <th class="list">
                <b>Sockets</b>
            </th>
            <th class="list">
                <b>Hyper</b>
            </th>
        </tr>
        <tr class="list" bgcolor="#FFFFFF">
            <td class="list">
                ${system.cpu.vendor}
            </td>
            <td class="list">
                ${system.cpu.model_name}
            </td>
            <td class="list">
                ${system.cpu.model}
            </td>
            <td class="list">
                ${system.cpu.family}
            </td>
            <td class="list">
                ${system.cpu.stepping}
            </td>
            <td class="list">
                ${system.cpu.speed}
            </td>
            <td class="list">
                ${system.cpu.processors}
            </td>
            <td class="list">
                ${system.cpu.cores}
            </td>
            <td class="list">
                ${system.cpu.sockets}
            </td>
            <td class="list">
                ${system.cpu.hyper}
            </td>
        </tr>
        <tr class="list">
            <th class="list">
                <b>Flags</b>
            </th>
            <td class="list" colspan="9" BGCOLOR="#f1f1f1">
              <span py:for="flag in system.cpu.flags">
               ${flag.flag}
              </span>
            </td>
        </tr>
      </table>
     </span>
    <br/>
    &nbsp;&nbsp;<b>Devices</b>
    <table class="list">
        <tr class="list">
            <th class="list">
                <b>Description</b>
            </th>
            <th class="list">
                <b>Type</b>
            </th>
            <th class="list">
                <b>Bus</b>
            </th>
            <th class="list">
                <b>Driver</b>
            </th>
            <th class="list">
                <b>Vendor ID</b>
            </th>
            <th class="list">
                <b>Device ID</b>
            </th>
            <th class="list">
                <b>Subsys Vendor ID</b>
            </th>
            <th class="list">
                <b>Subsys Device ID</b>
            </th>
        </tr>
        <?python row_color = "#FFFFFF" ?>
        <tr class="list" bgcolor="${row_color}" py:for="device in system.devices">
            <td class="list">
                <a class="list" href="${tg.url('/devices/view/%s' % device.id)}">${device.description}</a>
            </td>
            <td class="list">
                ${device.device_class}
            </td>
            <td class="list" align="center">
                ${device.bus}
            </td>
            <td class="list">
                ${device.driver}
            </td>
            <td class="list">
                ${device.vendor_id}
            </td>
            <td class="list">
                ${device.device_id}
            </td>
            <td class="list">
                ${device.subsys_vendor_id}
            </td>
            <td class="list">
                ${device.subsys_device_id}
            </td>
            <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
        </tr>
    </table>
     </div>
     <div class="tabbertab"><h2>Key/Values</h2>
     </div>
     <div class="tabbertab"><h2>Groups</h2>
      <p py:content="system_group_form(method='GET', action=system_group_action, groups=system.groups, value=value, options=options)">System Group Form goes here</p>
     </div>
     <div class="tabbertab"><h2>Excluded Families</h2>
     </div>
     <div class="tabbertab"><h2>Power</h2>
     </div>
     <div class="tabbertab"><h2>Console</h2>
     </div>
     <div class="tabbertab"><h2>Notes</h2>
        <input id="new_note" class="submit" value="New Note" name="new_note" type="button"/>
        <div id="note_input">
             Seperate form or embedded form for new notes?
	</div>
    <table class="list">
        <?python row_color = "#FFFFFF" ?>
        <div py:for="note in system.notes">
            <tr class="list" bgcolor="${row_color}">
                <th class="list">User</th>
                <td class="list">${note.user}</td>
                <th class="list">Created</th>
                <td class="list">${note.created}</td>
            </tr>
            <tr>
                <th class="list">Note</th>
                <td class="list" colspan="3">${note.text}</td>
            </tr>
            <tr>
             <td>&nbsp;</td>
            </tr>
            <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
        </div>
    </table>
     </div>
     <div class="tabbertab"><h2>History</h2>
    <table class="list">
        <tr class="list">
            <th class="list">user</th>
            <th class="list">created</th>
            <th class="list">field_name</th>
            <th class="list">old_value</th>
            <th class="list">new_value</th>
        </tr>
        <?python row_color = "#FFFFFF" ?>
        <tr class="list" bgcolor="${row_color}" py:for="act in activity">
            <td class="list">${act.user}</td>
            <td class="list">${act.created}</td>
            <td class="list">${act.field_name}</td>
            <td class="list">${act.old_value}</td>
            <td class="list">${act.new_value}</td>
            <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
        </tr>
    </table>
     </div>
    </div>

</body>
</html>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
<title>${system.name}</title>
</head>
<body>

    <table class="list">
        <tr class="list">
            <th class="list">
                <b>System Name</b>
            </th>
            <td class="list">
                ${system.name}
            </td>
            <th class="list">
                <b>Vendor</b>
            </th>
            <td class="list">
                ${system.vendor}
            </td>
            <th class="list">
                <b>Model</b>
            </th>
            <td class="list">
                ${system.model}
            </td>
        </tr>
        <tr class="list">
            <th class="list">
                <b>Date Created</b>
            </th>
            <td class="list">
                ${system.date_added}
            </td>
            <th class="list">
                <b>Last Modification</b>
            </th>
            <td class="list">
                ${system.date_modified}
            </td>
            <th class="list">
                <b>Last Checkin</b>
            </th>
            <td class="list">
                ${system.date_lastcheckin}
            </td>
        </tr>
        <tr class="list">
            <th class="list">
                <b>Serial Number</b>
            </th>
            <td class="list">
                ${system.serial}
            </td>
            <th class="list">
                <b>Location</b>
            </th>
            <td class="list" colspan="2">
                ${system.location}
            </td>
        </tr>
        <tr class="list">
            <th class="list">
                <b>Lender</b>
            </th>
            <td class="list">
                ${system.lender}
            </td>
            <th class="list">
                <b>User</b>
            </th>
            <td class="list">
                ${system.user}
            </td>
            <th class="list">
                <b>Owner</b>
            </th>
            <td class="list">
                ${system.owner}
            </td>
        </tr>
        <tr class="list">
            <th class="list">
                <b>Memory</b>
            </th>
            <td class="list">
                ${system.memory}
            </td>
            <th class="list">
                <b>Architecture(s)</b>
            </th>
            <td class="list" colspan="2">
                <span py:for="arch in system.arch">
                   ${arch.arch}
                </span>
            </td>
        </tr>
    </table>
    <br/>
    <div class="tabber">
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
     <div class="tabbertab"><h2>Power</h2>
     </div>
     <div class="tabbertab"><h2>Console</h2>
     </div>
     <div class="tabbertab"><h2>Reservation</h2>
     </div>
     <div class="tabbertab"><h2>Notes</h2>
     </div>
     <div class="tabbertab"><h2>History</h2>
     </div>
    </div>

</body>
</html>

<div xmlns:py="http://purl.org/kid/ns#">
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
          <b>Family</b>
      </th>
      <th class="list">
          <b>Model</b>
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
          ${system.cpu.family}
      </td>
      <td class="list">
          ${system.cpu.model}
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
  <tr class="list">
      <th class="list">
          <b>Arch(s)</b>
      </th>
      <td class="list" colspan="9" BGCOLOR="#ffffff">
         <span py:for="arch in system.arch">
            ${arch.arch}
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

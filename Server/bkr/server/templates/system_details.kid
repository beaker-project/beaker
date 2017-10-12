<div xmlns:py="http://purl.org/kid/ns#">

<section py:if="system.cpu">
<h3>CPU</h3>
<table class="table table-vertical">
  <tbody>
    <tr>
      <th>Vendor</th>
      <td>
          ${system.cpu.vendor}
      </td>
    </tr>
    <tr>
      <th style="white-space: nowrap;">Model Name</th>
      <td>
          ${system.cpu.model_name}
      </td>
    </tr>
    <tr>
      <th>Family</th>
      <td>
          ${system.cpu.family}
      </td>
    </tr>
    <tr>
      <th>Model</th>
      <td>
          ${system.cpu.model}
      </td>
    </tr>
    <tr>
      <th>Stepping</th>
      <td>
          ${system.cpu.stepping}
      </td>
    </tr>
    <tr>
      <th>Speed</th>
      <td>
          ${system.cpu.speed}
      </td>
    </tr>
    <tr>
      <th>Processors</th>
      <td>
          ${system.cpu.processors}
      </td>
    </tr>
    <tr>
      <th>Cores</th>
      <td>
          ${system.cpu.cores}
      </td>
    </tr>
    <tr>
      <th>Sockets</th>
      <td>
          ${system.cpu.sockets}
      </td>
    </tr>
    <tr>
      <th>Hyper</th>
      <td>
          ${system.cpu.hyper}
      </td>
    </tr>
    <tr>
      <th>Flags</th>
      <td>
        <span py:for="flag in system.cpu.flags">
         ${flag.flag}
        </span>
      </td>
    </tr>
    <tr>
      <th>Arch(s)</th>
      <td>
         <span py:for="arch in system.arch">
            ${arch.arch}
         </span>
      </td>
    </tr>
  </tbody>
</table>
</section>

<section py:if="system.disks">
<h3>Disks</h3>
<table class="table table-striped">
  <thead>
    <tr>
      <th>Model</th>
      <th>Size</th>
      <th>Logical sector size</th>
      <th>Physical sector size</th>
    </tr>
  </thead>
  <tbody>
    <tr py:for="disk in system.disks" id="disk-${disk.id}">
        <td>
            ${disk.model}
        </td>
        <td>
            ${'%0.2f' % (disk.size / 1000.**3)} GB /
            ${'%0.2f' % (disk.size / 1024.**3)} GiB
        </td>
        <td>
            ${disk.sector_size} bytes
        </td>
        <td>
            ${disk.phys_sector_size} bytes
        </td>
    </tr>
  </tbody>
</table>
</section>

<section>
<h3>Devices</h3>
<table class="table table-striped">
  <thead>
    <tr>
      <th>Description</th>
      <th>Type</th>
      <th>Bus</th>
      <th>Driver</th>
      <th>Vendor ID</th>
      <th>Device ID</th>
      <th>Subsys Vendor ID</th>
      <th>Subsys Device ID</th>
      <th>Firmware Version</th>
    </tr>
  </thead>
  <tbody>
    <tr py:for="device in system.devices">
        <td>
            <a href="${tg.url('/devices/view/%s' % device.id)}">${device.description}</a>
        </td>
        <td>
            ${device.device_class}
        </td>
        <td>
            ${device.bus}
        </td>
        <td>
            ${device.driver}
        </td>
        <td>
            ${device.vendor_id}
        </td>
        <td>
            ${device.device_id}
        </td>
        <td>
            ${device.subsys_vendor_id}
        </td>
        <td>
            ${device.subsys_device_id}
        </td>
        <td>
            ${device.fw_version}
        </td>
    </tr>
  </tbody>
</table>
</section>

</div>

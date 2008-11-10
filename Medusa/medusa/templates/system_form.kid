<form xmlns:py="http://purl.org/kid/ns#"
    name="${name}"
    action="${tg.url(action)}"
    method="${method}"
    py:attrs="form_attrs" width="100%">

    <div xmlns:py="http://purl.org/kid/ns#">
     ${display_field_for("id")}
     <table class="list">
      <tr class="list">
       <th class="list">
        <b>System Name</b>
       </th>
       <td class="list" colspan="5">
        ${display_field_for("fqdn")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Date Created</b>
       </th>
       <td class="list">
        ${value_for("date_added")}
       </td>
       <th class="list">
        <b>Last Modification</b>
       </th>
       <td class="list">
        ${value_for("date_modified")}
       </td>
       <th class="list">
        <b>Last Checkin</b>
       </th>
       <td class="list">
        ${value_for("date_lastcheckin")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Vendor</b>
       </th>
       <td class="list">
        ${display_field_for("vendor")}
       </td>
       <th class="list">
        <b>Lender</b>
       </th>
       <td class="list">
        ${display_field_for("lender")}
       </td>
       <th class="list">
        <b>Model</b>
       </th>
       <td class="list">
        ${display_field_for("model")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Serial Number</b>
       </th>
       <td class="list">
        ${display_field_for("serial")}
       </td>
       <th class="list">
        <b>Location</b>
       </th>
       <td class="list">
        ${display_field_for("location")}
       </td>
       <th class="list">
        <b>Condition</b>
       </th>
       <td class="list">
        ${display_field_for("status_id")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Owner</b>
       </th>
       <td class="list">
        ${value_for("owner")}
        <a py:if="owner_change_text" href="${owner_change}?id=${id}">
         <span py:content="owner_change_text"/>
        </a>
       </td>
       <th class="list">
        <b>Shared</b>
       </th>
       <td class="list">
        ${display_field_for("shared")}
       </td>
       <th class="list">
        <b>Current User</b>
       </th>
       <td class="list">
        ${value_for("user")}
        <a py:if="user_change_text" href="${user_change}?id=${id}">
         <span py:content="user_change_text"/>
        </a>
       </td>
      </tr>
      <tr>
       <th class="list">
        <b>Private</b>
       </th>
       <td class="list">
        ${display_field_for("private")}
       </td>
       <th class="list">
        <b>Type</b>
       </th>
       <td class="list">
        ${display_field_for("type_id")}
       </td>
       <th class="list">
        <b>Lab Controller</b>
       </th>
       <td class="list">
        ${display_field_for("lab_controller_id")}
       </td>
      </tr>
      <tr py:if="not readonly">
       <td colspan="6">
        <a class="button" href="javascript:document.${name}.submit();">Save Changes</a>
       </td>
      </tr>
     </table>
    </div>
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
    &nbsp;&nbsp;<b>Devices</b>
    <table class="list">
        <tr class="list">
            <th class="list">
                <b>Key</b>
            </th>
            <th class="list">
                <b>Value</b>
            </th>
            <th class="list">
                <b>&nbsp;</b>
            </th>
        </tr>
        <tr class="list" py:if="not readonly">
            <td class="list">
                ${display_field_for("key_name")}
            </td>
            <td class="list">
                ${display_field_for("key_value")}
            </td>
            <td class="list"><a class="button" href="javascript:document.${name}.submit();">Add ( + )</a></td>
        </tr>
        <tr class="list" bgcolor="${row_color}" py:for="key_value in system.key_values">
            <td class="list">
                ${key_value.key_name}
            </td>
            <td class="list">
                ${key_value.key_value}
            </td>
            <td class="list"><a py:if="not readonly" class="button" href="${tg.url('/key_remove', system_id=id, key_value_id=key_value.id)}">Delete ( - )</a></td>
         <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
        </tr>
    </table>
     </div>
     <div class="tabbertab"><h2>Groups</h2>
      <table class="list">
       <tr class="list">
        <th class="list">
         <b>Name</b>
        </th>
        <th class="list">
         <b>Display Name</b>
        </th>
        <th class="list">
         <b>&nbsp;</b>
        </th>
       </tr>
       <tr class="list" py:if="not readonly">
        <td class="list">
         ${display_field_for("group")}
        </td>
        <td class="list">
         &nbsp;
        </td>
        <td class="list">
         <a class="button" href="javascript:document.${name}.submit();">Add ( + )</a>
        </td>
       </tr>
       <tr class="list" bgcolor="${row_color}" py:for="group in system.groups">
        <td class="list">
         ${group.group_name}
        </td>
        <td class="list">
         ${group.display_name}
        </td>
        <td class="list">
         <a py:if="not readonly" class="button" href="${tg.url('/group_remove', system_id=id, group_id=group.group_id)}">Delete ( - )</a>
        </td>
         <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
       </tr>
      </table>
     </div>
     <div class="tabbertab"><h2>Excluded Families</h2>
     </div>
     <div class="tabbertab"><h2>Power</h2>
     </div>
     <div class="tabbertab"><h2>Console</h2>
     </div>
     <div class="tabbertab"><h2>Notes</h2>
      <div py:if="not readonly">
        ${display_field_for("note")}
         <a class="button" href="javascript:document.${name}.submit();">Add ( + )</a>
       <br/>
       <br/>
      </div>
      <table class="list">
       <?python row_color = "#F1F1F1" ?>
       <div py:for="note in system.notes">
        <tr class="list" bgcolor="${row_color}">
         <th class="list">User</th>
         <td class="list">${note.user}</td>
         <th class="list">Created</th>
         <td class="list">${note.created}</td>
        </tr>
        <tr>
         <th class="list">Note</th>
         <td class="list" colspan="3"><pre>${note.text}</pre></td>
        </tr>
        <tr>
         <td>&nbsp;</td>
        </tr>
       </div>
      </table>
     </div>
     <div class="tabbertab"><h2>Install Options</h2>
     </div>
     <div class="tabbertab"><h2>Provision</h2>
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
<!--        <tr class="list" bgcolor="${row_color}" py:for="act in activity">
            <td class="list">${act.user}</td>
            <td class="list">${act.created}</td>
            <td class="list">${act.field_name}</td>
            <td class="list">${act.old_value}</td>
            <td class="list">${act.new_value}</td>
            <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
        </tr> -->
    </table>
     </div>
    </div>
</form>

<div xmlns:py="http://purl.org/kid/ns#">
 <script language="JavaScript" type="text/JavaScript">
<!--
function confirmSubmit(action)
{
    var agree=confirm("Are you sure you wish to " + action + "?");
    if (agree) {

        if (${not is_user and 1 or 0}) { //1 if we are not the user, otherwise 0
             
            var agree_again=confirm("You are NOT the user of this machine, are you SURE you wish to " + action + "?");
            if (!agree_again)
                return false
        }
	    return true ;
    } else {
	    return false ;
    }
}
// -->
 </script>
<div py:if="tg.identity.anonymous" class="alert alert-info">You are not logged in.</div>
<div py:if="not tg.identity.anonymous and not can_power" class="alert alert-info">You do not have permission to control this system.</div>
<div py:if="not tg.identity.anonymous and can_power and not power_enabled" class="alert alert-info">System is not configured for power support.</div>
<div class="btn-toolbar">
    <form action="${action}" method="${method}">
      ${id.display(value_for(id), **params_for(id))}
      <div class="btn-group">
        <button class="btn" type="submit"
                name="action" value="on"
                py:attrs="(not can_power or not power_enabled) and {'disabled': ''} or {}"
                onclick="return confirmSubmit('power the system on');">
          Power On
        </button>
        <button class="btn" type="submit"
                name="action" value="off"
                py:attrs="(not can_power or not power_enabled) and {'disabled': ''} or {}"
                onclick="return confirmSubmit('power the system off');">
          Power Off
        </button>
        <button class="btn" type="submit"
                name="action" value="reboot"
                py:attrs="(not can_power or not power_enabled) and {'disabled': ''} or {}"
                onclick="return confirmSubmit('reboot the system');">
          Reboot
        </button>
        <button class="btn" type="submit"
                name="action" value="interrupt"
                py:attrs="(not can_power or not power_enabled) and {'disabled': ''} or {}"
                onclick="return confirmSubmit('interrupt the system');">
          Interrupt
        </button>
      </div>
    </form>
    <form action="../systems/clear_netboot_form" method="post">
      <input type="hidden" name="fqdn" value="${fqdn}" />
      <div class="btn-group">
        <button class="btn" type="submit"
                py:attrs="(not can_power or not netboot_enabled) and {'disabled': ''} or {}"
                onclick="return confirmSubmit('clear the system\'s netboot configuration');">
          Clear Netboot
        </button>
      </div>
    </form>
</div>
</div>

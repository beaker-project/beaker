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
 <span py:if="enabled">
    <form action="${tg.url(action)}" method="${method}">
      ${id.display(value_for(id), **params_for(id))}
      <div class="btn-group">
        <button class="btn" type="submit"
                name="action" value="on"
                onclick="return confirmSubmit('power the system on');">
          Power On
        </button>
        <button class="btn" type="submit"
                name="action" value="off"
                onclick="return confirmSubmit('power the system off');">
          Power Off
        </button>
        <button class="btn" type="submit"
                name="action" value="reboot"
                onclick="return confirmSubmit('reboot the system');">
          Reboot
        </button>
        <button class="btn" type="submit"
                name="action" value="interrupt"
                onclick="return confirmSubmit('interrupt the system');">
          Interrupt
        </button>
      </div>
    </form>
 </span>
 <span py:if="not enabled">System is not configured for power support</span>
</div>


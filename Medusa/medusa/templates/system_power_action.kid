<div xmlns:py="http://purl.org/kid/ns#">
 <script language="JavaScript" type="text/JavaScript">
<!--
function confirmSubmit(action)
{
var agree=confirm("Are you sure you wish to " + action + "?");
if (agree)
	return true ;
else
	return false ;
}
// -->
 </script>
 <span py:if="enabled">
  <form onSubmit="return confirmSubmit('Power System On');"
   name="${name}_off"
   action="${tg.url(action)}"
   method="${method}" width="100%">
       ${id.display(value_for(id), **params_for(id))}
       <input type="hidden" name="action" value="on" class="hiddenfield"/>
       <input type="Submit" value="Power On System" id="on" name="on"/>
  </form>
  <form onSubmit="return confirmSubmit('Power System Off');"
   name="${name}_on"
   action="${tg.url(action)}"
   method="${method}" width="100%">
       ${id.display(value_for(id), **params_for(id))}
       <input type="hidden" name="action" value="off" class="hiddenfield"/>
       <input type="Submit" value="Power Off System" id="off" name="off"/>
  </form>
  <form onSubmit="return confirmSubmit('Reboot System');"
   name="${name}_reboot"
   action="${tg.url(action)}"
   method="${method}" width="100%">
       ${id.display(value_for(id), **params_for(id))}
       <input type="hidden" name="action" value="reboot" class="hiddenfield"/>
       <input type="Submit" value="Reboot System" id="reboot" name="reboot"/>
  </form>
 </span>
 <span py:if="not enabled">System is not configured for power support</span>
</div>


<form xmlns:py="http://purl.org/kid/ns#"
 name="${name}"
 action="${tg.url(action)}"
 method="${method}" width="100%">
 <span py:if="lab_controller and will_provision is True">
  <span py:if="not tg.identity.anonymous">
   <script language="JavaScript" type="text/JavaScript">
    ${name}_0 = new Provision('${id.field_id}', '${prov_install.field_id}', '${ks_meta.field_id}','${koptions.field_id}','${koptions_post.field_id}','${tg.url('/get_installoptions')}');
    addLoadEvent(${name}_0.initialize);
   </script>
   <table>
    <tr>
     <td rowspan="6">
      ${display_field_for("prov_install")}
     </td>
    </tr>
    <tr>
     <td><label class="fieldlabel"
                for="${ks_meta.field_id"
                py:content="ks_meta.label"/>
     </td>
     <td>${display_field_for("ks_meta")}
     </td>
    </tr>
    <tr>
     <td><label class="fieldlabel"
                for="${koptions.field_id"
                py:content="koptions.label"/>
     </td>
     <td>${display_field_for("koptions")}
     </td>
    </tr>
    <tr>
     <td><label class="fieldlabel"
                for="${koptions_post.field_id"
                py:content="koptions_post.label"/>
     </td>
     <td>${display_field_for("koptions_post")}
     </td>
    </tr>
    <span py:if="provision_now_rights">
    <tr py:if="power_enabled">
     <td>${display_field_for("reboot")}</td>
     <td><label class="fieldlabel"
                for="${reboot.field_id"
                py:content="reboot.label"/>
     </td>
    </tr>
    <tr py:if="not power_enabled">
     <td colspan="2">This system is not configured for reboot support</td>
    </tr>
    <tr>
     <td>&nbsp;</td>
     <td>
      <a class="button" href="javascript:document.${name}.submit();">Provision</a>
     </td>
    </tr>
    </span>
    <span py:if="not provision_now_rights">
    <tr> 
     <td><label class="fieldlabel" py:content="schedule_reserve_days.label"/>
     </td>
     <td>
     ${schedule_reserve_days.display()}
     </td>
    </tr>
    <tr>
     <td>&nbsp;</td>
     <td>
      <a class="button" href="javascript:document.${name}.submit();">Schedule provision</a>
     </td>
    </tr>
    </span>
   </table>

   ${display_field_for("id")}
  </span>
 </span>
  <span py:if="not will_provision and provision_now_rights">
   You can only provision if you have reserved the system.
  </span>
  <span py:if="not will_provision and not provision_now_rights">
   You do not have access to provision or schedule a job on this system.
  </span>

 <span py:if="not lab_controller">
  This system is not associated to a lab controller
 </span>
</form>

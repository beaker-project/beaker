<form xmlns:py="http://purl.org/kid/ns#"
 name="${name}"
 action="${tg.url(action)}"
 method="${method}" width="100%">
 <div xmlns:py="http://purl.org/kid/ns#" id="field_id">
  <table class="power">
   <tr>
    <td><label class="fieldlabel"
               for="${power_type_id.field_id}"
               py:content="power_type_id.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(power_type_id)"
            class="fielderror"
            py:content="error_for(power_type_id)" />
     </font>
     ${power_type_id.display(value_for(power_type_id), **params_for(power_type_id))}
     <span py:if="power_type_id.help_text"
           class="fieldhelp"
           py:content="power_type_id.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${power_address.field_id}"
               py:content="power_address.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(power_address)"
            class="fielderror"
            py:content="error_for(power_address)" />
     </font>
     ${power_address.display(value_for(power_address), **params_for(power_address))}
     <span py:if="power_address.help_text"
           class="fieldhelp"
           py:content="power_address.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${power_user.field_id}"
               py:content="power_user.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(power_user)"
            class="fielderror"
            py:content="error_for(power_user)" />
     </font>
     ${power_user.display(value_for(power_user), **params_for(power_user))}
     <span py:if="power_user.help_text"
           class="fieldhelp"
           py:content="power_user.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${power_passwd.field_id}"
               py:content="power_passwd.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(power_passwd)"
            class="fielderror"
            py:content="error_for(power_passwd)" />
     </font>
     ${power_passwd.display(value_for(power_passwd), **params_for(power_passwd))}
     <span py:if="power_passwd.help_text"
           class="fieldhelp"
           py:content="power_passwd.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${power_id.field_id}"
               py:content="power_id.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(power_id)"
            class="fielderror"
            py:content="error_for(power_id)" />
     </font>
     ${power_id.display(value_for(power_id), **params_for(power_id))}
     <span py:if="power_id.help_text"
           class="fieldhelp"
           py:content="power_id.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${release_action.field_id}"
               py:content="release_action.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(release_action)"
            class="fielderror"
            py:content="error_for(release_action)" />
     </font>
     ${release_action.display(value_for(release_action), **params_for(release_action))}
     <span py:if="release_action.help_text"
           class="fieldhelp"
           py:content="release_action.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${reprovision_distro_id.field_id}"
               py:content="reprovision_distro_id.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(reprovision_distro_id)"
            class="fielderror"
            py:content="error_for(reprovision_distro_id)" />
     </font>
     ${reprovision_distro_id.display(value_for(reprovision_distro_id), **params_for(reprovision_distro_id))}
     <span py:if="reprovision_distro_id.help_text"
           class="fieldhelp"
           py:content="reprovision_distro_id.help_text" />
    </td>
   </tr>
   <tr>
    <td>
     ${id.display(value_for(id), **params_for(id))}
    </td>
    <td>
     <a class="button" href="javascript:document.${name}.submit();">Save Power Changes</a>
    </td>
   </tr>
  </table>
 </div>
</form>


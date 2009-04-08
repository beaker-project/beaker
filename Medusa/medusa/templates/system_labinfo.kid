<form xmlns:py="http://purl.org/kid/ns#"
 name="${name}"
 action="${tg.url(action)}"
 method="${method}" width="100%">
 <div xmlns:py="http://purl.org/kid/ns#" id="field_id">
  <table>
   <tr>
    <td><label class="fieldlabel"
               for="${orig_cost.field_id}"
               py:content="orig_cost.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(orig_cost)"
            class="fielderror"
            py:content="error_for(orig_cost)" />
     </font>
     ${orig_cost.display(value_for(orig_cost), **params_for(orig_cost))}
     <span py:if="orig_cost.help_text"
           class="fieldhelp"
           py:content="orig_cost.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${curr_cost.field_id}"
               py:content="curr_cost.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(curr_cost)"
            class="fielderror"
            py:content="error_for(curr_cost)" />
     </font>
     ${curr_cost.display(value_for(curr_cost), **params_for(curr_cost))}
     <span py:if="curr_cost.help_text"
           class="fieldhelp"
           py:content="curr_cost.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${dimensions.field_id}"
               py:content="dimensions.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(dimensions)"
            class="fielderror"
            py:content="error_for(dimensions)" />
     </font>
     ${dimensions.display(value_for(dimensions), **params_for(dimensions))}
     <span py:if="dimensions.help_text"
           class="fieldhelp"
           py:content="dimensions.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${weight.field_id}"
               py:content="weight.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(weight)"
            class="fielderror"
            py:content="error_for(weight)" />
     </font>
     ${weight.display(value_for(weight), **params_for(weight))}
     <span py:if="weight.help_text"
           class="fieldhelp"
           py:content="weight.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${wattage.field_id}"
               py:content="wattage.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(wattage)"
            class="fielderror"
            py:content="error_for(wattage)" />
     </font>
     ${wattage.display(value_for(wattage), **params_for(wattage))}
     <span py:if="wattage.help_text"
           class="fieldhelp"
           py:content="wattage.help_text" />
    </td>
   </tr>
   <tr>
    <td><label class="fieldlabel"
               for="${cooling.field_id}"
               py:content="cooling.label"/>
    </td>
    <td>
     <font color="red">
      <span py:if="error_for(cooling)"
            class="fielderror"
            py:content="error_for(cooling)" />
     </font>
     ${cooling.display(value_for(cooling), **params_for(cooling))}
     <span py:if="cooling.help_text"
           class="fieldhelp"
           py:content="cooling.help_text" />
    </td>
   </tr>
   <tr>
    <td>
     ${id.display(value_for(id), **params_for(id))}
    </td>
    <td>
     <a class="button" href="javascript:document.${name}.submit();">Save Lab Info Changes</a>
    </td>
   </tr>
  </table>
 </div>
</form>


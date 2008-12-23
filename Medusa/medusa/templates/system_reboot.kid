<form xmlns:py="http://purl.org/kid/ns#"
 name="${name}"
 action="${tg.url(action)}"
 method="${method}" width="100%">
 <div xmlns:py="http://purl.org/kid/ns#" id="field_id">
     ${id.display(value_for(id), **params_for(id))}
     <a py:if="enabled" class="button" href="javascript:document.${name}.submit();">Reboot System</a>
 </div>
</form>


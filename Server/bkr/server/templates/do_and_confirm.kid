<form action="${action}" method="post" xmlns:py="http://purl.org/kid/ns#">
  <script>
    var success_action = function(form_node) {
        return function() { form_node.submit(); }}
    var confirm_it = function (form_node) {
        do_and_confirm_form('${msg}', '${action_text}',
            success_action(form_node));
    }
  </script>
  <span py:for="field in hidden_fields"
    py:replace="field.display()"/>
    <a py:if="look == 'link'"
      href="#"
      onclick="javascript:confirm_it(this.parentNode);return false;">
      ${action_text}</a>
    <button py:if="look == 'button'" class="btn"
      onclick="javascript:confirm_it(this.parentNode);return false;">
      ${action_text}</button>
</form>

<div xmlns:py="http://purl.org/kid/ns#">
<style type="text/css">
textarea {
  font-family: monospace !important;
}
</style>
<div py:if="xsd_errors" class="alert alert-block alert-error">
  <h4>Job failed schema validation. Please confirm that you want to submit it.</h4>
        <ul class="xsd-error-list">
            <li py:for="error in xsd_errors">
                Line ${error.line}, col ${error.column}: ${error.message}
            </li>
        </ul>
</div>
<form
    name="${use_name and name or None}"
    id="${not use_name and name or None}"
    action="${action}"
    method="${method}"
    py:attrs="form_attrs"
    class="clone-job"
>
        <div py:for="field in hidden_fields"
            py:replace="field.display(value_for(field), **params_for(field))"
        />
  <div class="row-fluid">
    <div class="span10">
      <textarea name="textxml" rows="40" class="input-block-level">${value_for('textxml')}</textarea>
    </div>
    <div class="span2">
      <button type="submit" class="btn btn-primary btn-block queue-button">${submit_text}</button>
<script type='text/javascript'>
    $('.queue-button').affix({
          offset: {
            top: $('.queue-button').offset().top,
          }
    });
</script>
    </div>
  </div>
</form>
</div>

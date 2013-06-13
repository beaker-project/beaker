<form xmlns:py="http://purl.org/kid/ns#"
    id="${name}"
    action="${action}"
    method="${method}"
    class="form-horizontal"
    py:attrs="form_attrs"
>
<?python
from turbogears.widgets import CheckBox
?>
    <div py:if="hidden_fields" style="display:none">
        <div py:for="field in hidden_fields"
            py:replace="field.display(value_for(field), **params_for(field))"
        />
    </div>
    <fieldset>
        <legend py:if="legend_text" py:content="legend_text" />
        <div py:for="field in fields" class="control-group ${error_for(field) and 'error' or ''}">
            <!--! check boxes are a special case :-( -->
            <span py:strip="True" py:if="isinstance(field, CheckBox)">
                <div class="controls">
                    <label class="checkbox">
                        <span py:replace="field.display(value_for(field), **params_for(field))" />
                        ${field.label}
                    </label>
                    <span py:if="field.help_text" class="help-block" py:content="field.help_text" />
                    <span py:if="error_for(field)" class="help-block error" py:content="error_for(field)" />
                </div>
            </span>
            <span py:strip="True" py:if="not isinstance(field, CheckBox)">
                <label class="control-label" for="${field.field_id}" py:content="field.label" />
                <div class="controls">
                    <span py:replace="field.display(value_for(field), **params_for(field))" />
                    <span py:if="field.help_text" class="help-block" py:content="field.help_text" />
                    <span py:if="error_for(field)" class="help-block error" py:content="error_for(field)" />
                </div>
            </span>
        </div>
        <div class="form-actions">
            <button type="submit" class="btn btn-primary" py:content="submit_text" />
        </div>
    </fieldset>
</form>

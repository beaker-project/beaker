<form xmlns:py="http://purl.org/kid/ns#"
    id="${name}"
    action="${action}"
    method="${method}"
    class="form-inline"
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
    <span py:for="field in fields" class="control-group ${error_for(field) and 'error' or ''}">
        <!--! check boxes are a special case :-( -->
        <span py:strip="True" py:if="isinstance(field, CheckBox)">
            <label class="checkbox">
                <span py:replace="field.display(value_for(field), **params_for(field))" />
                ${field.label}
            </label>
        </span>
        <span py:strip="True" py:if="not isinstance(field, CheckBox)">
            <label class="control-label" for="${field.field_id}" py:content="field.label" />
            <span py:replace="field.display(value_for(field), **params_for(field))" />
        </span>
        <span py:if="error_for(field)" class="help-inline">${error_for(field)}</span>
    </span>
    <button type="submit" class="btn btn-primary" py:content="submit_text" />
</form>

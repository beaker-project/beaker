<div xmlns:py="http://purl.org/kid/ns#">
<div py:if="xsd_errors">
    <center>
        <div class="flash">Job failed schema validation. Please confirm that you want to submit it.</div>
        <ul class="xsd-error-list">
            <li py:for="error in xsd_errors">
                Line ${error.line}, col ${error.column}: ${error.message}
            </li>
        </ul>
    </center>
</div>
<!--!copied from TableForm, because I couldn't find a better way of composing this widget -->
<form
    name="${use_name and name or None}"
    id="${not use_name and name or None}"
    action="${action}"
    method="${method}"
    class="tableform"
    py:attrs="form_attrs"
>
    <div py:if="hidden_fields" style="display:none">
        <div py:for="field in hidden_fields"
            py:replace="field.display(value_for(field), **params_for(field))"
        />
    </div>
    <table border="0" cellspacing="0" cellpadding="2">
        <tr>
            <td>&#160;</td>
            <td py:content="submit.display(submit_text)" />
        </tr>
        <tr py:for="i, field in enumerate(fields)" class="${i%2 and 'odd' or 'even'}">
            <th>
                <label class="fieldlabel" for="${field.field_id}" py:content="field.label" />
            </th>
            <td>
                <span py:replace="field.display(value_for(field), **params_for(field))" />
                <span py:if="error_for(field)" class="fielderror" py:content="error_for(field)" />
                <span py:if="field.help_text" class="fieldhelp" py:content="field.help_text" />
            </td>
        </tr>
        <tr>
            <td>&#160;</td>
            <td py:content="submit.display(submit_text)" />
        </tr>
    </table>
</form>
</div>

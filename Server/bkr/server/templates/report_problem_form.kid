<div xmlns:py="http://purl.org/kid/ns#">
<script type='text/javascript' src="${tg.url('/static/javascript/util.js')}"/>
    <div py:if="hidden_fields" style="display:none">
        <div py:for="field in hidden_fields"
            py:replace="field.display(value_for(field), **params_for(field))"
        />
    </div>
    <table border="0" cellspacing="0" cellpadding="2">
        <tr>
            <th>Problematic system</th>
            <td>${system.fqdn}</td>
        </tr>
        <tr py:if="recipe">
            <th>Related recipe</th>
            <td>${recipe.t_id}</td>
        </tr>
        <tr py:for="i, field in enumerate(fields)">
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
</div>

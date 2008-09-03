<div class="expanding_form" xmlns:py="http://purl.org/kid/ns#">
<table id="${field_id}">
    <thead><tr>
        <th py:for="field in fields">
            <span class="fieldlabel" py:content="field.label" />
        </th>
    </tr></thead>
    <tbody>
    <tr py:for="repetition in repetitions"
        class="${field_class}"
        id="${field_id}_${repetition}">
        
        <td py:for="field in fields">
                <span py:content="field.display(value_for(field),
                      **params_for(field))" />
                <span py:if="error_for(field)" class="fielderror"
                      py:content="error_for(field)" />
                <span py:if="field.help_text" class="fieldhelp"
                      py:content="field_help_text" />
        </td>
        <td>
            <a
            href="javascript:ExpandingForm.removeItem('${field_id}_${repetition}')">Remove (-)</a>
        </td>

    </tr>
    </tbody>
</table>
<a id="doclink" href="javascript:ExpandingForm.addItem('${field_id}');">Add ( + )</a>
</div>
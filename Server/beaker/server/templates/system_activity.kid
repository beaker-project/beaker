<div xmlns:py="http://purl.org/kid/ns#">
<span py:if="search_bar">${search_bar.display(method='GET', action=action, value=searchvalue, options=options)}</span>
${grid.display(list)}

</div>
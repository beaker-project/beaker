<div xmlns:py="http://purl.org/kid/ns#">
${search_bar.display(method='GET', action=action, value=searchvalue,options=options)}
<div style="float: left;">
    <a href="${all_history}">Clear search</a>
</div>
${grid.display(list)}
</div>

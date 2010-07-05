<div xmlns:py="http://purl.org/kid/ns#">
${search_bar.display(method='GET', action=tg.url(action), value=searchvalue,options=options)}
<span><a href="${all_history}">Clear search</a></span>

${grid.display(list)}
</div>

<html xmlns:py="http://purl.org/kid/ns#"> 
<div style="padding-top:0.5em;text-align:center">
<a py:for="letter in letters" style="padding:0 0.2em 0 0.2em;font-size:2em" href="${tg.request.path_info}?${keyword}.text.starts_with=${letter}">${letter}</a>
</div>
</html>

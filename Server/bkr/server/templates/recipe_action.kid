<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
<div>
<a class='list' href="${value.clone_link()}">Clone RecipeSet</a><br/>
<div py:if="report_link is not None and not tg.identity.anonymous" py:strip="1">
    ${report_link}
        <div id="${report_problem_options['name']}" style='display:none'>
            ${problem_form.display(
                options=report_problem_options,
                name=report_problem_options['name'],
                action=report_problem_options['action'])}
        </div>
</div>
</div>

</html>

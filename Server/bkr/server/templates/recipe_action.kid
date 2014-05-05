<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<div xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
  <a class="btn" href="${value.clone_link()}">Clone RecipeSet</a>
  <div py:if="value.status == recipe_status_reserved">
    <a class="btn" href="${value.return_reservation_link()}">Release System</a>
  </div>
  <div py:if="not tg.identity.anonymous and report_problem_options" py:strip="1">
    <a class="btn" href="#"
       onclick="show_field('report_problem_recipe_${value.id}', '${problem_form.desc}'); return false;"
       >Report Problem with System</a>
    <div id="${report_problem_options['name']}" style='display:none'>
      ${problem_form.display(options=report_problem_options,
          name=report_problem_options['name'],
          action=report_problem_options['action'])}
    </div>
  </div>
</div>

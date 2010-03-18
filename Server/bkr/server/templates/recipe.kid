<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Recipe</title>
</head>

 <?python
    if recipe.result:
        default = recipe.result.result == 'Pass' and 'ShowAll' or 'ShowFail'
    else:
        default = 'ShowFail'
 ?>

<script type="text/javascript">
 $(document).ready(function() {
    ShowResults();
    $("input[@name='results']").change(ShowResults);
 });

 function ShowResults()
 {
    switch ($("input[@name='results']:checked").val())
    {
        case 'all':
            $('.fail').show();
            $('.pass').show();
        break;
        case 'fail':
            $('.fail').show();
            $('.pass').hide();
        break;
    }
 }
</script>
<body class="flora">
 <table width="97%">
  <tr>
   <td>
    <div class="show"><a href="${tg.url('/jobs/%s' % recipe.recipeset.job.id)}">Job: ${recipe.recipeset.job.t_id}</a></div>
   </td>
  </tr>
 </table>
 <form>
  <input id="results_all" type="radio" name="results" value="all" checked="${(None, '')[default == 'ShowAll']}"/>
  <label for="results_all">All results</label>
  <input id="results_fail" type="radio" name="results" value="fail" checked="${(None, '')[default == 'ShowFail']}" />
  <label for="results_fail">Only failed items</label>
  <input id="results_ackneeded" type="radio" name="results" value="ackneeded" />
  <label for="results_ackneeded">Failed items needing review</label>
 </form>
 <div py:if="recipe_widget">
<p py:content="recipe_widget(recipe=recipe)">Recipe goes here</p>
 </div>
</body>
</html>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Job</title>
</head>

 <?python
    if job.result:
        default = job.result.result == 'Pass' and 'ShowAll' or 'ShowFail'
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
 <form>
  <input id="results_all" type="radio" name="results" value="all" checked="${(None, '')[default == 'ShowAll']}" />
  <label for="results_all">All results</label>
  <input id="results_fail" type="radio" name="results" value="fail" checked="${(None, '')[default == 'ShowFail']}" />
  <label for="results_fail">Only failed items</label>
  <input id="results_ackneeded" type="radio" name="results" value="ackneeded" />
  <label for="results_ackneeded">Failed items needing review</label>
 </form>

 <table width="97%" class="show">
  <tr>
   <td class="title"><b>Job ID</b></td>
   <td class="value"><a class="list" href="${tg.url('/jobs/%s' % job.id)}">${job.t_id}</a></td>
   <td class="title"><b>Status</b></td>
   <td class="value">${job.status}</td>
   <td class="title"><b>Result</b></td>
   <td class="value">${job.result}</td>
  </tr>
  <tr>
   <td class="title"><b>Owner</b></td>
   <td class="value">${job.owner}</td>
   <td class="title"><b>Progress</b></td>
   <td class="value">${job.progress_bar}</td>
   <td class="title"><b>Action(s)</b></td>
   <td class="value">${job.action_link}</td>
  </tr>
  <tr>
   <td class="title"><b>Whiteboard</b></td>
   <td class="value" colspan="5">${job.whiteboard}</td>
  </tr>
 </table>
  <div py:for="recipeset in job.recipesets" class="recipeset">
   <table width="97%">
    <tr>
     <td class="title"><b>RecipeSet ID</b></td>
     <td class="value">${recipeset.t_id}</td>
    </tr>
   </table>
   <div py:for="recipe in recipeset.recipes" class="recipe">
    <div py:content="recipe_widget(recipe=recipe)">Recipe goes here</div>
   </div>
  </div>
</body>
</html>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Recipe ${recipe.t_id} - ${recipe.recipeset.job.whiteboard}/${recipe.whiteboard} | ${recipe.status} | ${recipe.result}</title>
</head>

<body class="flora">
 <table width="97%">
  <tr>
   <td>
    <div class="show"><a href="${tg.url('/jobs/%s' % recipe.recipeset.job.id)}">Job: ${recipe.recipeset.job.t_id}</a></div>
   </td>
  </tr>
 </table>
 <div py:if="recipe_widget">
<p py:content="recipe_widget(recipe=recipe)">Recipe goes here</p>
 </div>
</body>
</html>

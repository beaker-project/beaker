<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>Recipe ${recipe.t_id} - ${recipe.recipeset.job.whiteboard}/${recipe.whiteboard} | ${recipe.status} | ${recipe.result}</title>
</head>

<body class="with-localised-datetimes">
<h1><a href="${tg.url('/jobs/%s' % recipe.recipeset.job.id)}">Job: ${recipe.recipeset.job.t_id}</a></h1>
<p py:content="recipe_widget(recipe=recipe)">Recipe goes here</p>
</body>
</html>

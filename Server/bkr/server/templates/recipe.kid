<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>${title}</title>
</head>
<body>
  <script type="text/javascript">
    var recipe = new Recipe(${tg.to_json(recipe.to_json(include_recipeset=True))},
        {parse: true, url: ${tg.to_json(tg.url(recipe.href))}});
    $(function () {
        new RecipePageHeaderView({model: recipe, el: $('.recipe-page-header')});
        new RecipeQuickInfoView({model: recipe, el: $('.recipe-quick-info')});
        new RecipeInstallationView({model: recipe, el: $('.recipe-installation')});
        new RecipeTasksView({model: recipe, el: $('.recipe-tasks')});
        new RecipeReservationView({model: recipe, el: $('.recipe-reservation')});
    });
    // auto-refresh while the job is not finished
    var autofetch = function () {
        if (!recipe.get('is_finished')) {
            recipe.fetch();
            _.delay(autofetch, 30000);
        }
    };
    _.delay(autofetch, 30000);
  </script>
  <div class="recipe-page-header"></div>
  <div class="recipe-quick-info"></div>
  <ul class="nav nav-tabs recipe-nav">
    <li><a data-toggle="tab" href="#recipe-installation">Installation</a></li>
    <li><a data-toggle="tab" href="#recipe-tasks">Tasks</a></li>
    <li><a data-toggle="tab" href="#recipe-reservation">Reservation</a></li>
  </ul>
  <div class="tab-content recipe-tabs">
    <div class="tab-pane recipe-installation" id="recipe-installation"></div>
    <div class="tab-pane recipe-tasks" id="recipe-tasks"></div>
    <div class="tab-pane recipe-reservation" id="recipe-reservation"></div>
  </div>
  <script type="text/javascript">
    $(function () { link_tabs_to_anchor('beaker_recipe_tabs', '.recipe-nav'); });
  </script>
</body>
</html>

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
        var layout = new RecipePageLayout({model: recipe});
        $('#container').append(layout.el);
        // Bootstrap tabs don't work properly until they are inserted into the DOM >:(
        // so we have to do this here, after insertion, and not inside .render()
        layout.update_viewstate_from_hash();
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
</body>
</html>

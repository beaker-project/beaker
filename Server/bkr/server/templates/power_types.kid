<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
  <title>${title}</title>
</head>
<body>
  <div class="page-header">
    <h1>${title}</h1>
  </div>
  <script type="text/javascript">
    var power_types = new PowerTypes(${tg.to_json(power_types)}, {url: ${tg.to_json(power_types_url)}});
    $(function () {
        new PowerTypesView({collection: power_types, el: $('#power-types ul'), user_can_edit: ${tg.to_json(user_can_edit)}});
        if ( ${tg.to_json(user_can_edit)} )
            new AddPowerTypeForm({collection: power_types, el: $('#power-types-add-form')});
    });
  </script>
  <div id="power-types">
    <ul class="list-group power-types-list">
    </ul>
  </div>
  <div id="power-types-add-form"></div>
</body>
</html>

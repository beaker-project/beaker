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
    var labcontrollers = new LabControllers(${tg.to_json(labcontrollers)}, {url: ${tg.to_json(labcontrollers_url)}});
    $(function () {
        new LabControllersView({collection: labcontrollers, el: $('#labcontrollers ul'), can_edit: ${tg.to_json(can_edit)}});
        new LabControllersManageView({collection: labcontrollers, el: $('#labcontrollers-add'), can_edit: ${tg.to_json(can_edit)}});
    });
  </script>
  <div id="labcontrollers">
    <ul class="list-group labcontrollers-list">
    </ul>
  </div>
  <div id="labcontrollers-add"></div>
</body>
</html>

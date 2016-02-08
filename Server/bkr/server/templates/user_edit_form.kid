<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title>${attributes['user_name']}</title>
</head>
<body>
  <div id="user-view"></div>
  <script type="text/javascript">
    var user = new User(${tg.to_json(attributes)}, {parse: true, url: ${tg.to_json(tg.url(url))}});
    $(function () {
        new UserView({model: user, el: $('#user-view')});
    });
  </script>
</body>
</html>

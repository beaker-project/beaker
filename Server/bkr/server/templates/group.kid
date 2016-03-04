<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
  <title>${title}</title>
</head>
<body>
  <script type="text/javascript">
    var group = new Group(${tg.to_json(group.to_json())}, {parse: true, url: ${tg.to_json(tg.url(group.href))}});
    $(function () {
        new GroupDetailsView({model: group, el: $('#group-details')});
        new GroupMembersListView({model: group, el: $('#members')});
        new GroupOwnersListView({model: group, el: $('#owners')});
        new GroupPermissionsListView({model: group, el: $('#permissions')});
        new GroupRootPasswordView({model: group, el: $('#rootpassword')});
    });
  </script>
  <div id="group-details" class="group-details"></div>
  <ul class="nav nav-tabs group-nav">
    <li><a data-toggle="tab" href="#members">Members</a></li>
    <li><a data-toggle="tab" href="#owners">Owners</a></li>
    <li><a data-toggle="tab" href="#permissions">Permissions</a></li>
    <li><a data-toggle="tab" href="#rootpassword">Root Password</a></li>
  </ul>
  <div class="tab-content group-tabs">
    <div class="tab-pane" id="members"></div>
    <div class="tab-pane" id="owners"></div>
    <div class="tab-pane" id="permissions"></div>
    <div class="tab-pane" id="rootpassword"></div>
  </div>
  <script type="text/javascript">
    $(function () { link_tabs_to_anchor('beaker_group_tabs', '.group-nav'); });
  </script>
</body>
</html>

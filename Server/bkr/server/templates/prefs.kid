<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

    <title>User Preferences</title>
</head>

<body>
<div class="page-header">
  <h1>User Preferences</h1>
</div>

<ul class="nav nav-tabs">
  <li><a data-toggle="tab" href="#root-password">Root Password</a></li>
  <li><a data-toggle="tab" href="#ssh-public-keys">SSH Public Keys</a></li>
  <li><a data-toggle="tab" href="#submission-delegates">Submission Delegates</a></li>
  <li><a data-toggle="tab" href="#ui">User Interface</a></li>
  <li><a data-toggle="tab" href="#user-notifications">Notifications</a></li>
  <li><a data-toggle="tab" href="#keystone-trust">OpenStack Keystone Trust</a></li>
</ul>

<div class="tab-content prefs-tabs">
  <div class="tab-pane" id="root-password"></div>
  <div class="tab-pane" id="ssh-public-keys"></div>
  <div class="tab-pane" id="submission-delegates"></div>
  <div class="tab-pane" id="ui"></div>
  <div class="tab-pane" id="user-notifications"></div>
  <div class="tab-pane keystone-trust" id="keystone-trust"></div>
</div>

<script type="text/javascript">
  var user = new User(${tg.to_json(attributes)}, {parse: true, url: ${tg.to_json(tg.url(user.href))}});
  $(function () {
      new UserRootPasswordView({
          model: user,
          el: $('#root-password'),
          default_root_password: ${tg.to_json(default_root_password)},
          default_root_passwords: ${tg.to_json(default_root_passwords)},
      });
      new UserSSHPublicKeysView({model:user, el: $('#ssh-public-keys')});
      new UserSubmissionDelegatesView({model:user, el: $('#submission-delegates')});
      new UserUIPreferencesView({model: user, el: $('#ui')});
      new UserNotificationsView({model:user, el: $('#user-notifications')});
      new UserKeystoneTrustView({model: user, el: $('#keystone-trust')});
      link_tabs_to_anchor('beaker_prefs_tabs', '.nav-tabs');
  });
</script>

</body>
</html>

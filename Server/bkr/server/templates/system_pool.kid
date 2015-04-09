<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
  <title>${title}</title>
</head>
<body>
  <script type="text/javascript">
    var system_pool = new SystemPool(${tg.to_json(system_pool)}, {parse: true, url: ${tg.to_json(tg.url(system_pool.href))}});
    $(function () {
        new SystemPoolInfo({model: system_pool, el: $('#system-pool-info')});
        new SystemPoolSystemsView({model: system_pool, el: $('#systems')});
        new SystemPoolAccessPolicyView({model: system_pool, el: $('#access-policy')});
    });
  </script>
  <div id="system-pool-info"></div>
  <ul class="nav nav-tabs system-pool-nav">
    <li><a data-toggle="tab" href="#systems">Systems</a></li>
    <li><a data-toggle="tab" href="#access-policy">System Access Policy</a></li>
  </ul>
  <div class="tab-content system-pool-tabs">
    <div class="tab-pane" id="systems"></div>
    <div class="tab-pane" id="access-policy"></div>
  </div>
  <script type="text/javascript">
    $(function () { link_tabs_to_anchor('beaker_system_pools_tabs', '.system-pool-nav'); });
  </script>
</body>
</html>

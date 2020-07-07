<!DOCTYPE html>
<?python import sitetemplate ?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" py:extends="sitetemplate">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'" py:attrs="item.items()">
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title py:replace="''">Your title goes here</title>
    <link rel="shortcut icon" href="${tg.url('/assets/favicon.ico')}"/>
    <link rel="icon" href="${tg.url('/assets/favicon.ico')}" sizes="16x16 32x32 64x64"/>
    <link rel="icon" href="${tg.url('/assets/favicon-32.png')}" sizes="32x32"/>
    <link rel="icon" href="${tg.url('/assets/favicon-152.png')}" sizes="152x152"/>
    <script type="text/javascript">
    window.beaker_url_prefix = ${tg.to_json(tg.url('/'))};
    </script>
    <link py:for="css in tg_css" py:replace="css.display()" />
    <link py:for="js in tg_js_head" py:replace="js.display()" />
    <script type="text/javascript" py:if="tg.identity.user">
    window.beaker_current_user = new User(${tg.to_json(tg.identity.user)});
    </script>
    <meta py:replace="item[:]"/>
</head>

<body py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'" py:attrs="item.items()">
<div py:for="js in tg_js_bodytop" py:replace="js.display()" />

<?python
from bkr.server.model import device_classes
from bkr.server.reports import Reports
?>
<nav class="navbar navbar-static-top">
    <div class="navbar-inner">
        <a class="brand" href="${tg.url('/')}">Beaker</a>
        <ul id="nav-left" class="nav">
            <li class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    Systems
                    <b class="caret"></b>
                </a>
                <ul class="dropdown-menu">
                    <li><a href="${tg.url('/')}">All</a></li>
                    <li><a href="${tg.url('/available/')}">Available</a></li>
                    <li><a href="${tg.url('/free/')}">Free</a></li>
                    <li><a href="${tg.url('/removed/')}">Removed</a></li>
                    <li><a href="${tg.url('/pools/')}">Pools</a></li>
                    <li><a href="${tg.url('/reserveworkflow/')}">Reserve</a></li>
                </ul>
            </li>
            <li class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    Devices
                    <b class="caret"></b>
                </a>
                <ul class="dropdown-menu">
                    <li><a href="${tg.url('/devices')}">All</a></li>
                    <li py:for="device_class in device_classes">
                        <a href="${tg.url('/devices/%s' % device_class)}">${device_class}</a>
                    </li>
                </ul>
            </li>
            <li class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    Distros
                    <b class="caret"></b>
                </a>
                <ul class="dropdown-menu">
                    <li><a href="${tg.url('/distros')}">All</a></li>
                    <li><a href="${tg.url('/distrotrees/')}">Trees</a></li>
                    <li><a href="${tg.url('/distrofamily')}">Family</a></li>
                </ul>
            </li>
            <li class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    Scheduler
                    <b class="caret"></b>
                </a>
                <ul class="dropdown-menu">
                    <li><a href="${tg.url('/jobs/new')}">New Job</a></li>
                    <li><a href="${tg.url('/jobs')}">Jobs</a></li>
                    <li><a href="${tg.url('/recipes')}">Recipes</a></li>
                    <li><a href="${tg.url('/tasks/new')}">New Task</a></li>
                    <li><a href="${tg.url('/tasks')}">Task Library</a></li>
                    <li><a href="${tg.url('/watchdogs')}">Watchdog</a></li>
                    <li><a href="${tg.url('/reserveworkflow/')}">Reserve</a></li>
                </ul>
            </li>
            <li class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    Reports
                    <b class="caret"></b>
                </a>
                <ul class="dropdown-menu">
                    <li><a href="${tg.url('/reports')}">Reserve</a></li>
                    <li><a href="${tg.url('/matrix')}">Matrix</a></li>
                    <li><a href="${tg.url('/csv')}">CSV</a></li>
                    <li><a href="${tg.url('/tasks/executed')}">Executed</a></li>
                    <li py:for="controller in Reports.extension_controllers" py:replace="controller.menu_item" />
                </ul>
            </li>
            <li class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    Activity
                    <b class="caret"></b>
                </a>
                <ul class="dropdown-menu">
                    <li><a href="${tg.url('/activity/')}">All</a></li>
                    <li><a href="${tg.url('/activity/system')}">Systems</a></li>
                    <li><a href="${tg.url('/activity/pool')}">System Pools</a></li>
                    <li><a href="${tg.url('/activity/labcontroller')}">Lab Controllers</a></li>
                    <li><a href="${tg.url('/activity/group')}">Groups</a></li>
                    <li><a href="${tg.url('/activity/distro')}">Distros</a></li>
                    <li><a href="${tg.url('/activity/distrotree')}">Distro Trees</a></li>
                </ul>
            </li>
            <li py:if="'admin' in tg.identity.groups" class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    Admin
                    <b class="caret"></b>
                </a>
                <ul class="dropdown-menu">
                    <li><a href="${tg.url('/users/')}">Users</a></li>
                    <li><a href="${tg.url('/groups/')}">Groups</a></li>
                    <li><a href="${tg.url('/configuration')}">Configuration</a></li>
                    <li><a href="${tg.url('/retentiontag/admin')}">Retention Tags</a></li>
                    <li><a href="${tg.url('/labcontrollers')}">Lab Controllers</a></li>
                    <li><a href="${tg.url('/powertypes')}">Power Types</a></li>
                    <li><a href="${tg.url('/keytypes')}">Key Types</a></li>
                    <li><a href="${tg.url('/osversions')}">OS Versions</a></li>
                    <li><a href="${tg.url('/csv/csv_import')}">Import</a></li>
                    <li><a href="${tg.url('/csv')}">Export</a></li>
                </ul>
            </li>
        </ul>
        <ul id="nav-right" class="nav pull-right">
            <li py:if="not tg.identity.anonymous" class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    Hello<span class="navbar-wide-viewport-only">, ${tg.identity.user}</span>
                    <b class="caret"></b>
                </a>
                <ul class="dropdown-menu">
                    <li><a href="${tg.url('/prefs/')}">Preferences</a></li>
                    <li><a href="${tg.url('/users/' + tg.identity.user.user_name)}">My Account</a></li>
                    <li py:if="'admin' not in tg.identity.groups"><a href="${tg.url('/groups')}">Groups</a></li>
                    <li><a href="${tg.url('/mine')}">My Systems</a></li>
                    <li><a href="${tg.url('/pools/?q=owner.user_name:')}${tg.identity.user}">My System Pools</a></li>
                    <li><a href="${tg.url('/jobs/mine')}">My Jobs</a></li>
                    <li><a href="${tg.url('/jobs/mygroups')}">My Group Jobs</a></li>
                    <li><a href="${tg.url('/recipes/mine')}">My Recipes</a></li>
                    <li><a href="${tg.url('/groups/?q=member.user_name:' + tg.identity.user.user_name)}">My Groups</a></li>
                    <li><a href="${tg.url('/logout')}">Log out</a></li>
                </ul>
            </li>
            <li py:if="not tg.identity.anonymous" class="navbar-wide-viewport-only">
              <a href="${tg.url('/jobs/mine')}">My Jobs</a>
            </li>
            <li py:if="tg.identity.anonymous"><a href="${tg.login_url()}">Log in</a>
            </li>
            <li class="dropdown">
              <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                Help
                <b class="caret"></b>
              </a>
              <ul class="dropdown-menu" id="help-menu">
                <li><a href="${tg.config('beaker.documentation_link')}">Documentation</a></li>
                <li><a href="${tg.config('beaker.issue_create_link')}">Report a Bug</a></li>
              </ul>
            </li>
        </ul>
    </div>
</nav>

<div id="container" class="container-fluid">

    <?python
    from bkr.server import motd
    ?>
    <div class="alert motd alert-info alert-block" py:if="motd.get_motd()">
        <h4>Message of the day</h4>
        ${XML(motd.get_motd())}
    </div>

    <div class="alert flash" py:if="value_of('tg_flash', None)">
        ${tg_flash}
        <a class="close" data-dismiss="alert" href="#"><i class="fa fa-times" /></a>
    </div>

    <div py:replace="[item.text]+item[:]"/>

</div>

<footer>
  <p><a href="https://beaker-project.org/">Beaker</a> ${tg.beaker_version()}</p>
</footer>

<div py:for="js in tg_js_bodybottom" py:replace="js.display()" />
</body>

</html>

<!DOCTYPE html>
<?python import sitetemplate ?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" py:extends="sitetemplate">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'" py:attrs="item.items()">
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title py:replace="''">Your title goes here</title>
    <script type="text/javascript">
    window.beaker_url_prefix = ${tg.to_json(tg.url('/'))};
    </script>
    <meta py:replace="item[:]"/>
</head>

<body py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'" py:attrs="item.items()">

<?python
from bkr.server.model import device_classes
from bkr.server.reports import Reports
?>
<nav class="navbar navbar-static-top">
    <div class="navbar-inner">
        <a class="brand" href="${tg.url('/')}">Beaker</a>
        <ul class="nav">
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
                </ul>
            </li>
            <li class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    Devices
                    <b class="caret"></b>
                </a>
                <ul class="dropdown-menu">
                    <li><a href="${tg.url('/devices')}">All</a></li>
                    <li py:for="device_class in device_classes()">
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
                    <li><a href="${tg.url('/reserveworkflow')}">Reserve</a></li>
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
                    <li><a href="${tg.url('/reports/external')}">External</a></li>
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
                    <li><a href="${tg.url('/users')}">Accounts</a></li>
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
        <ul class="nav pull-right">
            <li py:if="not tg.identity.anonymous" class="dropdown">
                <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    Hello<span class="navbar-wide-viewport-only">, ${tg.identity.user}</span>
                    <b class="caret"></b>
                </a>
                <ul class="dropdown-menu">
                    <li><a href="${tg.url('/prefs')}">Preferences</a></li>
                    <li py:if="'admin' not in tg.identity.groups"><a href="${tg.url('/groups')}">Groups</a></li>
                    <li><a href="${tg.url('/mine')}">My Systems</a></li>
                    <li><a href="${tg.url('/jobs/mine')}">My Jobs</a></li>
                    <li><a href="${tg.url('/jobs/mygroups')}">My Group Jobs</a></li>
                    <li><a href="${tg.url('/recipes/mine')}">My Recipes</a></li>
                    <li><a href="${tg.url('/groups/mine')}">My Groups</a></li>
                </ul>
            </li>
            <li py:if="not tg.identity.anonymous" class="navbar-wide-viewport-only">
              <a href="${tg.url('/jobs/mine')}">My Jobs</a>
            </li>
            <li py:if="tg.identity.anonymous"><a href="${tg.url('/login')}">Log in</a>
            </li>
            <li py:if="not tg.identity.anonymous"><a href="${tg.url('/logout')}">Log out</a>
            </li>
        </ul>
    </div>
</nav>

<div class="container-fluid">

    <?python
    from bkr.server import motd
    ?>
    <div class="alert motd alert-info alert-block" py:if="motd.get_motd()">
        <h4>Message of the day</h4>
        ${XML(motd.get_motd())}
    </div>

    <div class="alert flash" py:if="value_of('tg_flash', None)">
        ${tg_flash}
        <a class="close" data-dismiss="alert" href="#"><i class="icon-remove" /></a>
    </div>

    <div py:replace="[item.text]+item[:]"/>

    <footer>
        <ul class="inline">
            <li>Version ${tg.beaker_version()}</li>
            <li><a href="${tg.config('beaker.bz_create_link')}">Report Bug</a></li>
            <li><a href="${tg.config('beaker.documentation_link')}">Documentation</a></li>
        </ul>
    </footer>

</div>

<span py:if="tg.config('piwik.base_url') and tg.config('piwik.site_id')" py:strip="True">
<!--! This is a modified version of the Piwik tracking code that uses DOM
      manipulation instead of document.write to inject the Piwik <script/>.
      This lets the document.ready event fire without waiting for Piwik to be
      loaded (in case the Piwik server is nonresponsive).

      The basic technique is described here:
        http://www.nczonline.net/blog/2009/06/23/loading-javascript-without-blocking/
      but we can use jQuery.getScript() to do all the hard work for us.
      -->
<!-- Piwik -->
<script type="text/javascript">
var pkBaseURL = (("https:" == document.location.protocol) ? "https:${tg.config('piwik.base_url')}" : "http:${tg.config('piwik.base_url')}");
jQuery.ajax({
    url: pkBaseURL + 'piwik.js',
    dataType: 'script',
    cache: true, // prevent jQuery appending a stupid timestamp parameter
    success: function () {
try {
var piwikTracker = Piwik.getTracker(pkBaseURL + "piwik.php", ${tg.config('piwik.site_id')});
piwikTracker.setCustomVariable(1, 'beaker_user', '${tg.identity.user}');
piwikTracker.trackPageView();
piwikTracker.enableLinkTracking();
} catch( err ) {}
    }
});
</script><noscript><p><img src="${tg.config('piwik.base_url')}piwik.php?idsite=${tg.config('piwik.site_id')}" style="border:0" alt="" /></p></noscript>
<!-- End Piwik Tracking Code -->
</span>
</body>

</html>

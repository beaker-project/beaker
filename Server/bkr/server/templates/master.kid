<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<?python import sitetemplate ?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" py:extends="sitetemplate">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'" py:attrs="item.items()">
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title py:replace="''">Your title goes here</title>

    <meta py:replace="item[:]"/>
    <style type="text/css">
        #pageLogin
        {
            font-size: 10px;
            font-family: verdana;
            text-align: right;
        }
        
        .hidden
         {
             display:none
         }
    </style>
    <style type="text/css" media="screen">
@import "${tg.url('/static/css/layout-uncompressed.css')}";
</style>
</head>

<body py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'" py:attrs="item.items()">

<?python
from bkr.server.model import device_classes
from bkr.server.reports import Reports
?>
<div id="fedora-header">
    <div style="float:left; margin-left:50px;">
        <ul id="menu">
            <li class="logo">
                <a href="${tg.url('/')}">
                  <img style="float:right;" alt="" src="${tg.url('/static/images/header-beaker_logo2.png')}"/>
                </a>
            </li>
            <li>Systems
                <ul id="systems">
                    <li>
                        <img class="corner_inset_left" alt="" src="${tg.url('/static/images/corner_inset_left.png')}"/>
                        <a href="${tg.url('/')}">All</a>
                        <img class="corner_inset_right" alt="" src="${tg.url('/static/images/corner_inset_right.png')}"/>
                    </li>
                    <li><a href="${tg.url('/available/')}">Available</a></li>
                    <li><a href="${tg.url('/free/')}">Free</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="${tg.url('/static/images/corner_left.png')}"/>
                        <img class="middle" alt="" src="${tg.url('/static/images/dot.gif')}"/>
                        <img class="corner_right" alt="" src="${tg.url('/static/images/corner_right.png')}"/>
                    </li>
                </ul>
            </li>
            <li>Devices
                <ul id="devices">
                    <li>
                        <img class="corner_inset_left" alt="" src="${tg.url('/static/images/corner_inset_left.png')}"/>
                        <a href="${tg.url('/devices')}">All</a>
                        <img class="corner_inset_right" alt="" src="${tg.url('/static/images/corner_inset_right.png')}"/>
                    </li>
                    <li py:for="device_class in device_classes()">
                     <a href="${tg.url('/devices/%s' % device_class)}">${device_class}</a>
                    </li>
                    <li class="last">
                        <img class="corner_left" alt="" src="${tg.url('/static/images/corner_left.png')}"/>
                        <img class="middle" alt="" src="${tg.url('/static/images/dot.gif')}"/>
                        <img class="corner_right" alt="" src="${tg.url('/static/images/corner_right.png')}"/>
                    </li>
                </ul>
            </li>
            <li>Distros
                <ul id="distros">
                    <li>
                        <img class="corner_inset_left" alt="" src="${tg.url('/static/images/corner_inset_left.png')}"/>
                        <a href="${tg.url('/distros')}">All</a> 
                        <img class="corner_inset_right" alt="" src="${tg.url('/static/images/corner_inset_right.png')}"/>
                    </li> 
                    <li><a href="${tg.url('/distrotrees/')}">Trees</a></li>
                    <li>   
                        <a href="${tg.url('/distrofamily')}">Family</a>
                    </li>
                    <li class="last">
                        <img class="corner_left" alt="" src="${tg.url('/static/images/corner_left.png')}"/>
                        <img class="middle" alt="" src="${tg.url('/static/images/dot.gif')}"/>
                        <img class="corner_right" alt="" src="${tg.url('/static/images/corner_right.png')}"/>
                    </li>
                </ul>
            </li>
            <li>Scheduler
                <ul id="scheduler">
                    <li>
                        <img class="corner_inset_left" alt="" src="${tg.url('/static/images/corner_inset_left.png')}"/>
                        <a href="${tg.url('/jobs/new')}">New Job</a>
                        <img class="corner_inset_right" alt="" src="${tg.url('/static/images/corner_inset_right.png')}"/>
                    </li>
                    <li><a href="${tg.url('/jobs')}">Jobs</a></li>
                    <li><a href="${tg.url('/recipes')}">Recipes</a></li>
                    <li><a href="${tg.url('/tasks/new')}">New Task</a></li>
                    <li><a href="${tg.url('/tasks')}">Task Library</a></li>
                    <li><a href="${tg.url('/watchdogs')}">Watchdog</a></li>
                    <li><a href="${tg.url('/reserveworkflow')}">Reserve</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="${tg.url('/static/images/corner_left.png')}"/>
                        <img class="middle" alt="" src="${tg.url('/static/images/dot.gif')}"/>
                        <img class="corner_right" alt="" src="${tg.url('/static/images/corner_right.png')}"/>
                    </li>
                </ul>
            </li>
            <li>Reports
                <ul id="reports">
                    <li>
                        <img class="corner_inset_left" alt="" src="${tg.url('/static/images/corner_inset_left.png')}"/>
                        <a href="${tg.url('/reports')}">Reserve</a>
                        <img class="corner_inset_right" alt="" src="${tg.url('/static/images/corner_inset_right.png')}"/>
                    </li>
                    <li><a href="${tg.url('/matrix')}">Matrix</a></li>
                    <li><a href="${tg.url('/csv')}">CSV</a></li>
                    <li><a href="${tg.url('/tasks/executed')}">Executed</a></li>
                    <li><a href="${tg.url('/reports/utilisation_graph')}">Utilisation Graph</a></li>
                    <li><a href="${tg.url('/reports/external')}">External</a></li>
                    <li py:for="controller in Reports.extension_controllers" py:replace="controller.menu_item" />
                    <li class="last">
                        <img class="corner_left" alt="" src="${tg.url('/static/images/corner_left.png')}"/>
                        <img class="middle" alt="" src="${tg.url('/static/images/dot.gif')}"/>
                        <img class="corner_right" alt="" src="${tg.url('/static/images/corner_right.png')}"/>
                    </li>
                </ul>
            </li>
            <li>Activity
                <ul id="Activity">
                    <li>
                        <img class="corner_inset_left" alt="" src="${tg.url('/static/images/corner_inset_left.png')}"/>
                        <a href="${tg.url('/activity/')}">All</a>
                        <img class="corner_inset_right" alt="" src="${tg.url('/static/images/corner_inset_right.png')}"/>
                    </li>
                    <li><a href="${tg.url('/activity/system')}">Systems</a></li>
                    <li><a href="${tg.url('/activity/labcontroller')}">Lab Controllers</a></li>
                    <li><a href="${tg.url('/activity/group')}">Groups</a></li>
                    <li><a href="${tg.url('/activity/distro')}">Distros</a></li>
                    <li><a href="${tg.url('/activity/distrotree')}">Distro Trees</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="${tg.url('/static/images/corner_left.png')}"/>
                        <img class="middle" alt="" src="${tg.url('/static/images/dot.gif')}"/>
                        <img class="corner_right" alt="" src="${tg.url('/static/images/corner_right.png')}"/>
                    </li>
                </ul>
            </li>
            <li py:if="'admin' in tg.identity.groups">Admin
                <ul id="admin">
                    <li>
                        <img class="corner_inset_left" alt="" src="${tg.url('/static/images/corner_inset_left.png')}"/>
                        <a href="${tg.url('/users')}">Accounts</a>
                        <img class="corner_inset_right" alt="" src="${tg.url('/static/images/corner_inset_right.png')}"/>
                    </li>
                    <li><a href="${tg.url('/groups/')}">Groups</a></li>
                    <li><a href="${tg.url('/configuration')}">Configuration</a></li>
                    <li><a href="${tg.url('/retentiontag/admin')}">Retention Tags</a></li>
                    <li><a href="${tg.url('/labcontrollers')}">Lab Controllers</a></li>
                    <li><a href="${tg.url('/powertypes')}">Power Types</a></li>
                    <li><a href="${tg.url('/keytypes')}">Key Types</a></li>
                    <li><a href="${tg.url('/osversions')}">OS Versions</a></li>
                    <li><a href="${tg.url('/csv/csv_import')}">Import</a></li>
                    <li><a href="${tg.url('/csv')}">Export</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="${tg.url('/static/images/corner_left.png')}"/>
                        <img class="middle" alt="" src="${tg.url('/static/images/dot.gif')}"/>
                        <img class="corner_right" alt="" src="${tg.url('/static/images/corner_right.png')}"/>
                    </li>
                </ul>
            </li>
            <li>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</li>
        </ul>
        <img style="float:left;" alt="" src="${tg.url('/static/images/menu_right.png')}"/>
    </div>
    <div style="float:right; margin-right:50px;">
        <img style="float:left;" alt="" src="${tg.url('/static/images/menu_left.png')}"/>
        <ul id="menu">
            <li>&nbsp;&nbsp;</li>
            <li py:if="not tg.identity.anonymous">Hello, ${tg.identity.user}
                <ul id="User">
                    <li>
                        <img class="corner_inset_left" alt="" src="${tg.url('/static/images/corner_inset_left.png')}"/>
                        <a href="${tg.url('/prefs')}">Preferences</a>
                        <img class="corner_inset_right" alt="" src="${tg.url('/static/images/corner_inset_right.png')}"/>
                    </li>
                    <li py:if="'admin' not in tg.identity.groups"><a href="${tg.url('/groups')}">Groups</a></li>
                    <li><a href="${tg.url('/mine')}">My Systems</a></li>
                    <li><a href="${tg.url('/jobs/mine')}">My Jobs</a></li>
                    <li><a href="${tg.url('/jobs/mygroups')}">My Group Jobs</a></li>
                    <li><a href="${tg.url('/recipes/mine')}">My Recipes</a></li>
                    <li><a href="${tg.url('/groups/mine')}">My Groups</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="${tg.url('/static/images/corner_left.png')}"/>
                        <img class="middle" alt="" src="${tg.url('/static/images/dot.gif')}"/>
                        <img class="corner_right" alt="" src="${tg.url('/static/images/corner_right.png')}"/>
                    </li>
                </ul>
            </li>
            <li py:if="not tg.identity.anonymous"><a href="${tg.url('/jobs/mine')}">My Jobs</a>
            </li>
            <li py:if="tg.identity.anonymous"><a href="${tg.url('/login')}">Login</a>
            </li>
            <li py:if="not tg.identity.anonymous"><a href="${tg.url('/logout')}">Logout</a>
            </li>
        </ul>
        <img style="float:left;" alt="" src="${tg.url('/static/images/menu_right.png')}"/>
    </div>
</div>

    <div id="fedora-nav"></div>
    <?python
    from bkr.server import motd
    ?>
    <div id='motd' py:if="motd.get_motd()">
    <p style='font-weight:bold;display:inline'>Message of the day</p>
    ${XML(motd.get_motd())}
    </div>
    <!-- header END -->
    <div id="fedora-middle-one">
        <div class="fedora-corner-tr">&nbsp;</div>
        <div class="fedora-corner-tl">&nbsp;</div>
        <div id="fedora-content">
            <center>
                <div id="status_block" class="flash" py:if="value_of('tg_flash', None)" py:content="tg_flash"></div>
           </center>
           <div py:replace="[item.text]+item[:]"/>

        </div>
        <div class="fedora-corner-br">&nbsp;</div>
        <div class="fedora-corner-bl">&nbsp;</div>
    </div>
    <div id="fedora-footer">
     <p>
     Version - ${tg.beaker_version()}
     <a href="${tg.config('beaker.bz_create_link')}">Report Bug</a>
     <a href="${tg.config('beaker.documentation_link')}">Documentation</a>
     </p>
    </div>
    <!-- End of main_content -->
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

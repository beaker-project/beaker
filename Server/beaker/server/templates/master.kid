<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<?python import sitetemplate ?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" py:extends="sitetemplate">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'" py:attrs="item.items()">
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title py:replace="''">Your title goes here</title>
    <script type="text/javascript" src="${tg.url('/static/javascript/jquery.js')}"></script>
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
from beaker.server.model import device_classes
from beaker.server.model import system_types
?>
<div id="fedora-header">
    <div style="float:left; margin-left:50px;">
        <ul id="menu">
            <li class="logo">
                <img style="float:right;" alt="" src="/static/images/header-beaker_logo2.png"/>
            </li>
            <li>Systems
                <ul id="systems">
                    <li>
                        <img class="corner_inset_left" alt="" src="/static/images/corner_inset_left.png"/>
                        <a href="${tg.url('/')}">All</a>
                        <img class="corner_inset_right" alt="" src="/static/images/corner_inset_right.png"/>
                    </li>
                    <li><a href="${tg.url('/mine/')}">Mine</a></li>
                    <li><a href="${tg.url('/available/')}">Available</a></li>
                    <li><a href="${tg.url('/free/')}">Free</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="/static/images/corner_left.png"/>
                        <img class="middle" alt="" src="/static/images/dot.gif"/>
                        <img class="corner_right" alt="" src="/static/images/corner_right.png"/>
                    </li>
                </ul>
            </li>
            <li>Devices
                <ul id="devices">
                    <li>
                        <img class="corner_inset_left" alt="" src="/static/images/corner_inset_left.png"/>
                        <a href="${tg.url('/devices')}">All</a>
                        <img class="corner_inset_right" alt="" src="/static/images/corner_inset_right.png"/>
                    </li>
                    <li py:for="device_class in device_classes()">
                     <a href="${tg.url('/devices/%s' % device_class)}">${device_class}</a>
                    </li>
                    <li class="last">
                        <img class="corner_left" alt="" src="/static/images/corner_left.png"/>
                        <img class="middle" alt="" src="/static/images/dot.gif"/>
                        <img class="corner_right" alt="" src="/static/images/corner_right.png"/>
                    </li>
                </ul>
            </li>
            <li>Distros
                <ul id="distros">
                    <li>
                        <img class="corner_inset_left" alt="" src="/static/images/corner_inset_left.png"/>
                        <a href="${tg.url('/distros')}">All</a>
                        <img class="corner_inset_right" alt="" src="/static/images/corner_inset_right.png"/>
                    </li>
                    <li><a href="${tg.url('/tags')}">Tags</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="/static/images/corner_left.png"/>
                        <img class="middle" alt="" src="/static/images/dot.gif"/>
                        <img class="corner_right" alt="" src="/static/images/corner_right.png"/>
                    </li>
                </ul>
            </li>
            <li>Scheduler
                <ul id="scheduler">
                    <li>
                        <img class="corner_inset_left" alt="" src="/static/images/corner_inset_left.png"/>
                        <a href="${tg.url('/jobs/new')}">New Job</a>
                        <img class="corner_inset_right" alt="" src="/static/images/corner_inset_right.png"/>
                    </li>
                    <li><a href="${tg.url('/jobs')}">Jobs</a></li>
                    <li><a href="${tg.url('/recipes')}">Recipes</a></li>
                    <li><a href="${tg.url('/tasks')}">Tasks</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="/static/images/corner_left.png"/>
                        <img class="middle" alt="" src="/static/images/dot.gif"/>
                        <img class="corner_right" alt="" src="/static/images/corner_right.png"/>
                    </li>
                </ul>
            </li>
            <li>Reports
                <ul id="reports">
                    <li>
                        <img class="corner_inset_left" alt="" src="/static/images/corner_inset_left.png"/>
                        <a href="${tg.url('/reports')}">Reserve</a>
                        <img class="corner_inset_right" alt="" src="/static/images/corner_inset_right.png"/>
                    </li>
                    <li><a href="${tg.url('/matrix')}">Matrix</a></li>
                    <li><a href="${tg.url('/reports')}">Executed</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="/static/images/corner_left.png"/>
                        <img class="middle" alt="" src="/static/images/dot.gif"/>
                        <img class="corner_right" alt="" src="/static/images/corner_right.png"/>
                    </li>
                </ul>
            </li>
            <li>Activity
                <ul id="Activity">
                    <li>
                        <img class="corner_inset_left" alt="" src="/static/images/corner_inset_left.png"/>
                        <a href="${tg.url('/activity')}">All</a>
                        <img class="corner_inset_right" alt="" src="/static/images/corner_inset_right.png"/>
                    </li>
                    <li><a href="${tg.url('/activity')}">Systems</a></li>
                    <li><a href="${tg.url('/activity')}">Distros</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="/static/images/corner_left.png"/>
                        <img class="middle" alt="" src="/static/images/dot.gif"/>
                        <img class="corner_right" alt="" src="/static/images/corner_right.png"/>
                    </li>
                </ul>
            </li>
            <li py:if="'admin' in tg.identity.groups">Admin
                <ul id="admin">
                    <li>
                        <img class="corner_inset_left" alt="" src="/static/images/corner_inset_left.png"/>
                        <a href="${tg.url('/users')}">Accounts</a>
                        <img class="corner_inset_right" alt="" src="/static/images/corner_inset_right.png"/>
                    </li>
                    <li><a href="${tg.url('/groups')}">Groups</a></li>
                    <li><a href="${tg.url('/labcontrollers')}">Lab Controllers</a></li>
                    <li><a href="${tg.url('/powertypes')}">Power Types</a></li>
                    <li><a href="${tg.url('/keytypes')}">Key Types</a></li>
                    <li><a href="${tg.url('/osversions')}">OS Versions</a></li>
                    <li><a href="${tg.url('/csv/csv_import')}">Import</a></li>
                    <li><a href="${tg.url('/csv')}">Export</a></li>
                    <li class="last">
                        <img class="corner_left" alt="" src="/static/images/corner_left.png"/>
                        <img class="middle" alt="" src="/static/images/dot.gif"/>
                        <img class="corner_right" alt="" src="/static/images/corner_right.png"/>
                    </li>
                </ul>
            </li>
            <li>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</li>
        </ul>
        <img style="float:left;" alt="" src="/static/images/menu_right.png"/>
    </div>
    <div style="float:right; margin-right:50px;">
        <img style="float:left;" alt="" src="/static/images/menu_left.png"/>
        <ul id="menu">
            <li py:if="tg.identity.anonymous"><a href="${tg.url('/login')}">Login</a>
            </li>
            <li py:if="not tg.identity.anonymous"><a href="${tg.url('/logout')}">Logout</a>
            </li>
            <li class="searchContainer">
                <div>
                <input type="text" id="searchField" />
                <img src="/static/images/magnifier.png" alt="Search" onclick="alert('You clicked on search button')" /></div>
                <ul id="search">
                    <li>
                        <img class="corner_inset_left" alt="" src="/static/images/corner_inset_left.png"/>
                        <input id="cbxAll" type="checkbox" />All
                        <img class="corner_inset_right" alt="" src="/static/images/corner_inset_right.png"/>
                    </li>
                    <li><input id="Systems" type="checkbox" />Systems</li>
                    <li><input id="Distros" type="checkbox" />Distros</li>
                    <li><input id="Jobs" type="checkbox" />Jobs</li>
                    <li><input id="Devices" type="checkbox" />Devices</li>
                    <li class="last">
                        <img class="corner_left" alt="" src="/static/images/corner_left.png"/>
                        <img class="middle" alt="" src="/static/images/dot.gif"/>
                        <img class="corner_right" alt="" src="/static/images/corner_right.png"/>
                    </li>
                </ul>
            </li>
        </ul>
        <img style="float:left;" alt="" src="/static/images/menu_right.png"/>
    </div>
</div>

    <div id="fedora-nav"></div>
    Version - ${tg.beaker_version()}
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
     <a href="${tg.config('beaker.bz_create_link')}">Report Bug</a>
     </p>
    </div>
    <!-- End of main_content -->
</body>

</html>

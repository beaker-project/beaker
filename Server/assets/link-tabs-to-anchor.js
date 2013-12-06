/*
 * Optional extra bits to link Bootstrap tabs to the anchor portion of the URL.
 *
 * Stores the current tab in the anchor (location.hash). Also sets 
 * a localStorage item as a fallback for cases where a form submission 
 * redirects us back to this page with no anchor.
 *
 * The page needs to call link_tabs_to_anchor after document.ready to opt in to 
 * this behaviour. Pass a jQuery selector for the tab container to link.
 *
 *      <script>
 *        $(function () { link_tabs_to_anchor('beaker_system_tabs', '.nav-tabs'); });
 *      </script>
 */

;(function () {

window.link_tabs_to_anchor = function (cookie_name, tab_selector) {
    var $tabs = $(tab_selector);
    $tabs.on('shown', 'a', function (e) {
        window.history.replaceState(undefined, undefined, $(this).attr('href'));
        localStorage.setItem(cookie_name, $(this).attr('href'));
    });
    var open_tab = function (href) {
        $tabs.find('a[href="' + href + '"]').tab('show');
    };
    $(window).on('hashchange', function () {
        open_tab(location.hash);
        return false;
    });
    if (location.hash) {
        open_tab(location.hash);
    } else if (localStorage.getItem(cookie_name)) {
        var href = localStorage.getItem(cookie_name);
        window.history.replaceState(undefined, undefined, href);
        open_tab(href);
    } else {
        $tabs.find('a:first').tab('show');
    }
};

})();

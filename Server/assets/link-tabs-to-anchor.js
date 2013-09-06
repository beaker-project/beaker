/*
 * Optional extra bits to link Bootstrap tabs to the anchor portion of the URL.
 *
 * Stores the current tab in the anchor (location.hash). Also stores a cookie 
 * as a fallback for cases where a form submission redirects us back to this 
 * page with no anchor.
 *
 * The page needs to call link_tabs_to_anchor after document.ready to opt in to 
 * this behaviour:
 *
 *      <script>$(link_tabs_to_anchor);</script>
 */

;(function () {

window.link_tabs_to_anchor = function () {
    $('.nav-tabs a').on('shown', function (e) {
        window.history.replaceState(undefined, undefined, $(this).attr('href'));
        $.cookie('beaker_system_tab', $(this).attr('href'));
    });
    var open_tab = function (href) {
        $('.nav-tabs a[href="' + href + '"]').tab('show');
    };
    $(window).on('hashchange', function () {
        open_tab(location.hash);
        return false;
    });
    if (location.hash) {
        open_tab(location.hash);
    } else if ($.cookie('beaker_system_tab')) {
        var href = $.cookie('beaker_system_tab');
        window.history.replaceState(undefined, undefined, href);
        open_tab(href);
    } else {
        $('.nav-tabs a:first').tab('show');
    }
};

})();

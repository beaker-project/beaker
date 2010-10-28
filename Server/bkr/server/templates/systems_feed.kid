<?python
import cherrypy
from bkr.server.util import absolute_url
?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:py="http://purl.org/kid/ns#">
    <title type="text">${title}</title>
    <id>${cherrypy.request.browser_url}</id>
    <link rel="self" type="application/atom+xml" href="${cherrypy.request.browser_url}"/>
    <!--updated></updated-->
    <entry py:for="system in list">
        <id>${absolute_url(system.href)}</id>
        <published>${system.date_added.isoformat()}</published>
        <updated py:if="system.date_modified">${system.date_modified.isoformat()}</updated>
        <title type="text">${system}</title>
        <link rel="alternate" type="text/html" href="${absolute_url(system.href)}" />
    </entry>
</feed>

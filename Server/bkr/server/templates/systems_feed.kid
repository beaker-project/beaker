<?python
import cherrypy
from bkr.server.util import absolute_url
from urlparse import urljoin
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
        <link rel="alternate" type="application/rdf+xml" href="${absolute_url(system.href + '?tg_format=rdfxml')}" />
        <link rel="alternate" type="application/x-turtle" href="${absolute_url(system.href + '?tg_format=turtle')}" />
    </entry>
</feed>

Preserve arbitrary XML
======================

Beaker preserves arbitrary XML elements at the top level in a separate
namespace. This can be any element and any namespace but must be a top-level
element under the root node. Beaker is not preserving position or order.

This is useful for jobs generated with third party tools when processing
instructions need to be stored and kept during cloning.

Example (shows a job XML snippet)::

    <job retention_tag="audit" group="somegroup" product="the_product">
        <b:option xmlns:b="http://example.com/bar">--foobar arbitrary</b:option>
        <f:test xmlns:f="http://example.com/foo">another element with content</f:test>
        <whiteboard>
            valid job
        </whiteboard>
        [...]

(Contributed by Róman Joost in :issue:`1112131`.)

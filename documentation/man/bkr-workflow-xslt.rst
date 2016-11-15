bkr workflow-xslt: XSLT-based Beaker job generator
==================================================

.. program:: bkr workflow-xslt

Synopsis
--------

| :program:`bkr workflow-xslt` [*options*]
|       [--defaults=<filename>] [--profile=<profile-name>] [--job-xml=<filename>]
|       [--dry-run | --wait]
|       [--xslt-override=<filename>] [--xslt-name=<name>] [--whiteboard=<text>]
|       [--save-xml=<filename>] [--save-internal-xml=<filename>]
|       [*job-specific options*]

Job-specific options are defined in the Job Configuration XML, and will be 
described with :option:`--help <bkr --help>`.

Description
-----------

This program will use a Job Configuration XML file which defines variables 
useful in a kernel workflow.  It will use this information to process the 
generate a Beaker job XML document, as defined in the configured XSLT files.

Beaker arguments
****************

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`. Note that, in spite of its 
name, this program does not accept the common workflow options described in the 
:ref:`Workflow options <workflow-options>` section of :manpage:`bkr(1)`.

It is important that the arguments in this section comes before any other 
options. These arguments define how the rest of the arguments should be 
processed and their default values.

.. option:: --defaults <filename>

   Adds more default values in addition to what may be configured in 
   :file:`~/.beaker-client/bks-defaults` and :file:`./bks-defaults`.

.. option:: --profile <profile-name>

   The defaults files can be configured with different profiles for the same 
   Job XML file. This argument will define which profile set to use for 
   default values.

.. option:: --job-xml <filename>

   Defines which Job XML Configuration file to load. This argument is 
   mandatory, unless configured in a defaults file.

.. option:: --dry-run

   When this option is used, the job will not be sent to the Beaker scheduler 
   at all. If you don't use :option:`--save-xml` or 
   :option:`--save-internal-xml` the generated Beaker job XML will be dumped to 
   stdout.

.. option:: --wait

   This will cause the :program:`bkr workflow-xslt` operation to wait for the 
   Beaker job to complete before exiting.

Global job arguments
********************

The global options are specific to the :program:`bkr workflow-xslt` module, and 
will use the defaults as defined in the *SETTINGS ARGUMENTS*. Short arguments 
may be overrided by the Job XML definition.

.. option:: --xslt-override <filename>

   This will override the configured XSLT file defined in the Job 
   Configuration.

.. option:: -X <name>, --xslt-name <name>

   The Job Configuration can have several XSLT templates configured. This 
   option will define which XSLT to use. If this option is not set, it will 
   use the XSLT template which has no name configured.

.. option:: -W <text>, --whiteboard <text>

   Adds the given <text> as a text for the Beaker job whiteboard.

.. option:: --save-xml <filename>

   Saves the generated Beaker Job XML to the given <filename>.

.. option:: --save-internal-xml <filename>

   Saves the internal XML document which is passed to the XSLT processor to the 
   given <filename>. This is useful during debugging.

Job XML configuration
*********************

A Job XML Configuration is needed to be able to generate XML files to the 
Beaker scheduler. The purpose of the Job XML Configuration is to define which 
parameters and variables which are needed for the XSLT processing to work. 
This configuration will also define parts of the XML document being sent to the 
XSLT processor. This configuration file is also an XML document.

It will not be explained how to write the needed XSLT documents in this manual.

The structure
~~~~~~~~~~~~~

::

    <JobConfig>
        <name>{Descriptive name of the job configuration}</name>
        <xslt>{Default XSLT file}</xslt>
        [<xslt name="variant2">{Named XSLT file}</xslt>]
        [...more <xslt/> tags...]
        <arguments>
            <arg section="recipe" type="{string|bool}" [optional="1"]>
                <name short="a">{long argument}</name>
                <tag type="{tagtype}">{XML tag name}</tag>
                [<default>{default value}</default>]
                <description>{Argument description</description>
                <metavar>{Descriptive value substitution<metavar>
            </arg>
            [...more <arg/> tags...]
        </arguments>
    </JobConfig>

Tag descriptions
~~~~~~~~~~~~~~~~

    <JobConfig/>
        The XML root node must be a <JobConfig/> tag.
    <name/>
        The first <name/> in <JobConfig/> is a plain and short string 
        describing the purpose of this Job Configuration.
    <xslt [name="{XSLT-NAME}"]/>
        This tag defines which XSLT templates this Job Configuration depends 
        on. It must be at least one <xslt/> present. If no ``name`` attribute 
        exists, it is defined as the default XSLT file. When the ``name`` 
        attribute is set, this XSLT file is used when using the 
        :option:`--xslt-name` option.
    <arguments/>
        All variable options the defined XSLT template needs must be configured 
        in separate <arg/> tags inside this tag.
    <arg section="recipe" type="{string|bool}">
        Each option individually is defined by <arg/> tags. The ``section`` 
        and ``type`` attributes are mandatory. Currently only the ``recipe`` 
        section is supported. The ``type`` attribute defines the type of 
        argument.  If the ``type`` attribute is set to ``bool`` it will define
        a command line argument which takes no arguments.  If this argument is
        given to ``bkr workflow-xslt``, it will result in the tag or attribute
        value being set to ``true``.  The ``optional`` attribute is optional.
        If set to ``1`` it will make this argument purely optional. The default
        is to require the argument.
    <name short="{short arg}"/>
        The <name/> defines the short and long option names. The ``short`` 
        attribute is mandatory and can only be one character. If the same 
        argument name is defined several times, the last defined argument will 
        override all other conflicting arguments.
    <tag type="{attribute|value|list}" [attrname="{Attribute name}"] [element_tag="{list element tag name}"]/>
        This tag defines which XML tag name the internal XML tag the option 
        value will be stored under. The ``type`` attribute is mandatory and can 
        be either ``attribute``, ``value`` or ``list``. When set to ``value`` the
        option value given at the command line of :program:`bkr workflow-xslt`
        will be embraced by the defined tag name. If ``type`` is set to ``attribute`` 
        the option value from the command line will be placed as an attribute 
        value to the defined XML tag name. When using ``attribute`` the ``attrname``
        attribute is mandatory. This attribute defines the attribute name to be used
        in the internal XML.  If ``type`` is set to ``list``, it will create a list of
        XML tags based on the value string.  The default value for the children of the
        tag name is 'value', unless the ``element_tag`` is set.  The value string will
        be split into separate tokens using comma (,) as the separator.
        
    <default/>
        This tag is optional. It will set a default value if this option is not 
        used on the command line.
    <description/>
        This tag is used for the :option:`--help <bkr --help>` screen, describing the 
        command line option to :program:`bkr workflow-xslt`.
    <metavar/>
        This is used for the :option:`--help <bkr --help>` screen as well. This is used as 
        a substitute for the variable contents, purely for. To make it obvious, 
        it is recommended to put use capital letters.

Example
~~~~~~~

Save the contents below as :file:`example-job.xml`::

    <?xml version="1.0"?>
    <jobConfig>
      <name>Example Job</name>
      <xslt>example.xsl</xslt>
      <arguments>
        <arg section="recipe" type="string">
          <name short="i">id</name>
          <metavar>INTEGER</metavar>
          <tag type="attribute" attrname="version">name</tag>
          <description>Unique numeric ID</description>
        </arg>
        <arg section="recipe" type="string">
          <name short="n">name</name>
          <metavar>FULL-NAME</metavar>
          <tag type="value">name</tag>
          <description>Full name</description>
        </arg>
        <arg section="recipe" type="string" optional="1">
          <name short="g">group</name>
          <metavar>GROUP-NAME</metavar>
          <tag type="attribute" attrname="group">name</tag>
          <description>Group identifier</description>
        </arg>
        <arg section="recipe" type="string" optional="1">
          <name>phone-numbers</name>
          <metavar>PHONE\-NUMBERS</metavar>
          <tag type="list" element_tag="number">phones</tag>
          <description>List of phone numbers, comma separated</description>
       </arg>
      </arguments>
    </jobConfig>

Save this dummy XSLT file as :file:`example.xsl`::

    <?xml version="1.0"?>
    <xsl:stylesheet version="1.0"
            xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
       <xsl:output method="xml" version="1.0"
               encoding="UTF-8" indent="yes"/>
    </xsl:stylesheet>

Run from a terminal the following command::

    $ bkr workflow-xslt --dry-run --job-xml example-job.xml \\
         --save-internal-xml example.xml \\
         -i 99 -n "Example" -g "Group1" --phone-numbers 123,456,789
    ----------------------------------------------------
    Generating Beaker XML
       Job config:    example-job.xml
       XSLT template: example.xsl
       Job name:      Example Job
       Whiteboard:    None
       Job arguments:
          - group: Group1
          - id: 99
          - name: Example
    ----------------------------------------------------
    $ cat example.xml
    <?xml version="1.0" encoding="UTF-8"?>
    <submit>
       <whiteboard/>
       <recipe>
         <phones>
            <number>123</number>
            <number>456</number>
            <number>789</number>
         </phones>
         <name group="Group1" version="99">Example</name>
       </recipe>
    </submit>

Setting defaults
****************

It is possible to define defaults in a separate file.  This is useful if you 
often use the same Job Configuration or have other arguments which do not 
change so often. Two files are attempted read upon startup: 
:file:`~/.beaker_client/bks-defaults` and :file:`./bks-defaults`.

The bks-defaults file is an INI-styled configuration file.  It requires 
a ``[defaults]`` section which has one parameter, ``jobxml``.

You can set individual default values depending on which Job XML Configuration 
you are using. Use the Job XML Configuration filename as the section name. 
The parameters uses the long options of the Job Configuration to define the 
default values.

Example
~~~~~~~

::

    [defaults]
    jobxml: example-job.xml

    [example-job.xml]
    group: Group1

Default profiles
~~~~~~~~~~~~~~~~

It is possible to define several sets of default values for the same Job XML 
Configuration. This is used by appending :<profilename> to the section name. 
Notice the 'colon'.

Example
~~~~~~~

This builds upon the example above::

    [example-job.xml:setup2]
    group: Group2b

To run the example in the Example section above, execute::

    $ bkr workflow-xslt --dry-run --save-internal-xml example.xml \\
        -i 99 -n "Example"

This will use the value ``Group1`` as a default value in the ``group`` 
attribute. If you instead do this::

    $ bkr workflow-xslt --dry-run --profile setup2 \\
        --save-internal-xml example.xml \\
        -i 99 -n "Example"

the generated example.xml will have the value ``Group2b`` as a default value in 
the ``group`` attribute.

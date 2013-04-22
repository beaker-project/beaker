System filtering using inventory date and status
================================================

A new XML element ``<last_inventoried>`` has been added to enable
system filtering using the date on which the system was last
inventoried. For example, to specify that your job should be run on a
system inventoried after 2013-01-02, you should add the following in
your job XML::

    <hostRequires>
        <system> <last_inventoried op="&gt;" value="2013-01-02" /> </system>
    </hostRequires>

Besides the above utility, this enhancement also allows you to use the
``bkr`` command line tool to list systems based on their last
inventoried status or date using the ``--xml-filter`` option.

(Contributed by Amit Saha in :issue:`949777`.)

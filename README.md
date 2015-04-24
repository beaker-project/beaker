Beaker is open-source software for managing and automating labs of test 
computers.

See the [Beaker homepage](http://beaker-project.org/) for further 
documentation and information about the Beaker project.
The [Developer guide](https://beaker-project.org/dev/guide/) in particular 
might be useful if you are working on Beaker.


Repo Layout
-----------

* `Server/`

    + `assets/`  
      Source files for static assets (JavaScript, LESS) which are served to the 
      web browser. The webassets module manages compilation and minification of 
      the raw source files into a form suitable for serving to the browser.

    + `bkr/server/tools/`  
      Various modules that are run as ancillary processes to the server.

    + `bkr/server/config/`  
      These are application specific configuration items.

    + `bkr/server/kickstarts/`  
      Kickstart templates that are served to the lab controller
      for provisioning test systems. See the
      [admin guide](https://beaker-project.org/docs/admin-guide/kickstarts.html)
      for further details.

    + `bkr/server/snippets/`  
      These are sections of kickstart templates that can be inserted into other
      kickstart templates as needed.

    + `bkr/server/static/`  
      Legacy static assets (not managed by the webassets module). No new assets 
      are added here.

    + `bkr/server/templates/`  
      Kid templates for TurboGears controller methods and TurboGears widgets.

    + `bkr/server/alembic/versions/`  
      Alembic database migration scripts.


* `LabController/`  
  This contains all the source code for the lab controller.

    + `addDistro/`  
      Scripts to run on the import of distros.
      See the [admin guide](https://beaker-project.org/docs/admin-guide/distro-import.html#automated-jobs-for-new-distros)
      for details.

    + `apache/beaker-lab-controller.conf`  
      Apache configuration file. Used to configure the serving of various files
      including logs.

    + `apache/404.html`  
      Custom 404 error page for logs.

    + `aux/anamon`, `aux/anamon.init`  
      "Anamon", the Anaconda monitoring script. This runs during Anaconda
      installations and periodically uploads Anaconda logs to Beaker.

    + `cron.hourly/`  
      Anything to be run as a cron job on the lab controller goes in here.
      Currently contains a single script that expires distros.

    + `init.d/`  
      Contains the init scripts for the individual lab controller processes.

    + `src/bkr/labcontroller/`  
      Modules that act as entry points for the main processes listed in
      init.d/, as well as related modules.

    + `src/bkr/labcontroller/power-scripts/`  
      Contains scripts responsible for power cycling test machines.


* `IntegrationTests/`  
  This directory contains the complete Beaker test suite. Tests for the server, 
  lab controller and client are found in their corresponding directories in 
  the `src/bkr/inttest/` directory.


* `Client/`  
  All source files for the beaker client are found here.

    + `src/bkr/client/`  
      Modules that are shared and utilized by various commands.

    + `src/bkr/client/commands/`  
      Each module in this directory corresponds to a different subcommand for 
      the `bkr` client. Man pages for each subcommand are included as 
      a module-level docstring in reStructuredText format.


* `documentation/`  
  Beaker's [documentation](https://beaker-project.org/docs/) in 
  reStructuredText format.


* `SchemaUpgrades/`  
  Legacy database upgrade instructions, for Beaker versions up to 0.8.2. Newer 
  database upgrades are managed by Alembic, with migration scripts added to 
  `Server/bkr/server/alembic/versions/`.


* `Common/`  
  Any substantial amount of source code that can be utilized by more than one
  package should be here.

    + `bkr/common/schema/`  
      Any kind of beaker entity that has a schema definition, will be defined
      here. This does not include database schemas.


* `Misc/`  
  Utilities and scripts which are used for developing Beaker but which do not 
  form part of the source tree itself.

    + `rpmbuild.sh`  
      Builds SRPM or RPM development packages from the current git HEAD 
      revision.
      For example, `Misc/rpmbuild.sh -bb` will perform a local RPM build 
      resulting in packages like `beaker-*-20.1-0.git.2.2dff0c7.noarch.rpm`.

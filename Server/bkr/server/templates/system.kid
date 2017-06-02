<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

 <head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
  <title>${title}</title>
  <script type="text/javascript">
    var system = new System(${tg.to_json(value)}, {parse: true, url: ${tg.to_json(tg.url('/systems/%s/' % value.fqdn))}});
    var distro_picker_options = ${tg.to_json(widgets_options['distro_picker'])};
    $(function () {
        if (system.get('can_change_fqdn')) {
            // XXX renaming is an extremely uncommon operation, it probably 
            // doesn't make sense to place the UI for it so prominently...
            $('.page-header h1').append(' ').append(new SystemRenameButton({model: system}).el);
        }
        new SystemQuickInfo({model: system, el: $('.system-quick-info')});
        new SystemOwnerView({model: system, el: $('#owner')});
        new SystemPoolView({model: system, el: $('#pools')});
        new SystemHardwareDetailsView({model: system, el: $('.system-hardware-details')});
        new SystemHardwareEssentialsView({model: system, el: $('#essentials')});
        new SystemProvisionView({
            model: system,
            el: $('#provision'),
            distro_picker_options: distro_picker_options,
        });
        new SystemLoanView({model: system, el: $('#loan')});
        new SystemPowerSettingsView({
            model: system,
            el: $('#power-settings'),
            distro_picker_options: distro_picker_options,
        });
        new SystemSchedulerSettingsView({model: system, el: $('#scheduler-settings')});
        new SystemNotesView({model: system, el: $('#notes')});
        new SystemAccessPolicyView({model: system, el: $('#access-policy')});
        new SystemActivityView({model: system, el: $('#history')});
        new SystemExecutedTasksView({model: system, el: $('#tasks')});
        new SystemCommandsView({model: system, el: $('#power')});
        // We defer the HTTP requests to populate these grids until the
        // relevant tab is shown. This way we avoid the extra requests if the 
        // user doesn't care about them.
        $('.system-nav a[href="#history"]').one('show', function () {
            system.activity.fetch({reset: true});
        });
        $('.system-nav a[href="#tasks"]').one('show', function () {
            system.executed_tasks.fetch({reset: true});
        });
        $('.system-nav a[href="#power"]').one('show', function () {
            system.command_queue.fetch({reset: true});
        });
    });
  </script>
 </head>

<body class="with-localised-datetimes">
  <div class="page-header"><h1>${value.fqdn}</h1></div>
  <div class="system-quick-info"></div>
  <div class="system-main-content">
    <ul class="nav nav-list system-nav">
      <li class="nav-header">Hardware</li>
      <li><a data-toggle="tab" href="#essentials">Essentials</a></li>
      <li><a data-toggle="tab" href="#details">Details</a></li>
      <li><a data-toggle="tab" href="#keys">Key/Values</a></li>
      <li py:if="widgets['labinfo']"><a data-toggle="tab" href="#labinfo">Lab Info</a></li>
      <li class="nav-header">Control</li>
      <li><a data-toggle="tab" href="#power">Power</a></li>
      <li><a data-toggle="tab" href="#provision">Provision</a></li>
      <li class="nav-header">Access</li>
      <li><a data-toggle="tab" href="#owner">Owner</a></li>
      <li><a data-toggle="tab" href="#pools">Pools</a></li>
      <li><a data-toggle="tab" href="#loan">Loan</a></li>
      <li><a data-toggle="tab" href="#access-policy">Access Policy</a></li>
      <li class="nav-header">Configuration</li>
      <li><a data-toggle="tab" href="#power-settings">Power Settings</a></li>
      <li><a data-toggle="tab" href="#scheduler-settings">Scheduler Settings</a></li>
      <li><a data-toggle="tab" href="#exclude">Excluded Families</a></li>
      <li><a data-toggle="tab" href="#install">Install Options</a></li>
      <li><a data-toggle="tab" href="#notes">Notes</a></li>
      <li class="nav-header">History</li>
      <li><a data-toggle="tab" href="#history">Activity</a></li>
      <!--
      <li><a data-toggle="tab" href="#IMPLEMENTME">Reservations</a></li>
      <li><a data-toggle="tab" href="#IMPLEMENTME">Loans</a></li>
      -->
      <li><a data-toggle="tab" href="#tasks">Executed Tasks</a></li>
    </ul>
    <div class="tab-content system-tabs">
      <div class="tab-pane" id="essentials"/>
      <div class="tab-pane" id="details">
        <div class="system-hardware-details"></div>
    ${widgets['details'].display(system=value)} 
      </div>
   <div class="tab-pane" id="keys">
    ${widgets['keys'].display(method='get', action=widgets_action['keys'], value=value, options=widgets_options['keys'])} 
   </div>
      <div class="tab-pane" id="owner"></div>
   <div class="tab-pane" id="pools"> </div>
      <div class="tab-pane" id="loan"></div>
      <div class="tab-pane" id="access-policy"></div>
   <div class="tab-pane" id="exclude">
    <span py:if="value.lab_controller and value.arch">
     ${widgets['exclude'].display(method='get', action=widgets_action['exclude'], value=value, options=widgets_options['exclude'])} 
    </span>
    <span py:if="not value.lab_controller or not value.arch">
     System must be associated to a lab controller and have at least one architecture specified to edit exclude families.
    </span>
   </div>
      <div class="tab-pane" id="power"></div>
      <div class="tab-pane" id="power-settings"></div>
      <div class="tab-pane" id="scheduler-settings"></div>
      <div class="tab-pane" id="notes"></div>
   <div class="tab-pane" id="install">
    <span py:if="value.lab_controller and value.arch">
     ${install_widget.display(method='get', action=widgets_action['install'], value=value, options=widgets_options['install'])}
    </span>
    <span py:if="not value.lab_controller or not value.arch">
     System must be associated to a lab controller and have at least one architecture specified to edit install options.
    </span>
   </div>
      <div class="tab-pane" id="provision"/>
   <div class="tab-pane" id="labinfo" py:if="widgets['labinfo']">
    ${widgets['labinfo'].display(method='get', action=widgets_action['labinfo'], value=value, options=widgets_options['labinfo'])}
   </div>
      <div class="tab-pane" id="history"></div>
      <div class="tab-pane" id="tasks"></div>
    </div>
  </div>
  <script type="text/javascript">
    $(function () { link_tabs_to_anchor('beaker_system_tabs', '.system-nav'); });
  </script>
 </body>
</html>

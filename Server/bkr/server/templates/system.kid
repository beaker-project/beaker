<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

 <head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
  <title>${title}</title>
  <script type="text/javascript">
    var system = new System(${tg.to_json(value)}, {parse: true, url: ${tg.to_json(tg.url('/systems/%s/' % value.fqdn))}});
    $(function () {
        new SystemQuickInfo({model: system, el: $('.system-quick-info')});
        new SystemOwnerView({model: system, el: $('#owner')});
        new SystemHardwareDetailsView({model: system, el: $('.system-hardware-details')});
        new SystemHardwareEssentialsView({model: system, el: $('#essentials')});
        new SystemLoanView({model: system, el: $('#loan')});
    });
  </script>
 </head>

<body>
  <div class="page-header">
    <h1>${value.fqdn}</h1>
  </div>
  <div class="system-quick-info"></div>
  <div class="row-fluid">
    <ul class="span3 nav nav-list system-nav">
      <li class="nav-header">Hardware</li>
      <li><a data-toggle="tab" href="#essentials">Essentials</a></li>
      <li><a data-toggle="tab" href="#details">Details</a></li>
      <li><a data-toggle="tab" href="#keys">Key/Values</a></li>
      <li py:if="widgets['labinfo']"><a data-toggle="tab" href="#labinfo">Lab Info</a></li>
      <li class="nav-header">Control</li>
      <li><a data-toggle="tab" href="#commands">Commands</a></li>
      <li><a data-toggle="tab" href="#provision">Provision</a></li>
      <li class="nav-header">Access</li>
      <li><a data-toggle="tab" href="#owner">Owner</a></li>
      <li><a data-toggle="tab" href="#groups">Groups</a></li>
      <li><a data-toggle="tab" href="#loan">Loan</a></li>
      <li><a data-toggle="tab" href="#access-policy">Access Policy</a></li>
      <li class="nav-header">Configuration</li>
      <li><a data-toggle="tab" href="#power">Power</a></li>
      <li><a data-toggle="tab" href="#IMPLEMENTME">Scheduler</a></li>
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
    <div class="span9 tab-content system-tabs">
      <div class="tab-pane" id="essentials"/>
      <div class="tab-pane" id="details">
        <div class="system-hardware-details"></div>
    ${widgets['details'].display(system=value)} 
      </div>
   <div class="tab-pane" id="keys">
    ${widgets['keys'].display(method='get', action=widgets_action['keys'], value=value, options=widgets_options['keys'])} 
   </div>
      <div class="tab-pane" id="owner"></div>
   <div class="tab-pane" id="groups">
    ${groups_widget.display(method='get', action=widgets_action['groups'], value=value, options=widgets_options['groups'])}
   </div>
      <div class="tab-pane" id="loan"></div>
   <div class="tab-pane" id="access-policy">
    <div id="access-policy-${value.id}">
      <i class="icon-spinner icon-spin"/> Loading&hellip;
    </div>
    <script>
      $(function () {
        // defer until tab is shown
        $('.system-nav a[href="#access-policy"]').one('show', function () {
          var policy = new AccessPolicy({}, {url:
              ${tg.to_json(tg.url('/systems/%s/access-policy' % value.fqdn))}});
          policy.fetch({
            success: function () {
              new AccessPolicyView({model: policy, el: '#access-policy-${value.id}',
                    readonly: ${tg.to_json(not tg.identity.user or not value.can_edit_policy(tg.identity.user))}});
            },
            error: function (model, xhr) {
              $('#access-policy-${value.id}').addClass('alert alert-error')
                .html('Failed to fetch access policy: ' + xhr.statusText);
            },
          });
        });
      });
    </script>
   </div>
   <div class="tab-pane" id="exclude">
    <span py:if="value.lab_controller and value.arch">
     ${widgets['exclude'].display(method='get', action=widgets_action['exclude'], value=value, options=widgets_options['exclude'])} 
    </span>
    <span py:if="not value.lab_controller or not value.arch">
     System must be associated to a lab controller and have at least one architecture specified to edit exclude families.
    </span>
   </div>
   <div class="tab-pane" id="commands">
      ${widgets['commands_form'].display(method='get', action=widgets_action['commands_form'], value=value, options=widgets_options['commands_form'])}
      <h3>Recent Commands</h3>
     ${widgets['power_history'].display(list=widgets_options['power_history'], title='Recent Commands')}
   </div>
   <div class="tab-pane" id="power">
    <span py:if="not readonly" py:strip="True">
     <span py:if="value.lab_controller" py:strip="True">
      ${widgets['power'].display(method='get', action=widgets_action['power'], value=value, options=widgets_options['power'])}
     </span>
     <span py:if="not value.lab_controller" py:strip="True">
      System must be associated to a lab controller to edit power settings.
     </span>
    </span>
    <span py:if="readonly" py:strip="True">
      You do not have access to edit power settings for this system.
    </span>
   </div>
   <div class="tab-pane" id="notes">
    ${widgets['notes'].display(method='get', action=widgets_action['notes'], value=value, options=widgets_options['notes'])} 
   </div>
   <div class="tab-pane" id="install">
    <span py:if="value.lab_controller and value.arch">
     ${install_widget.display(method='get', action=widgets_action['install'], value=value, options=widgets_options['install'])}
    </span>
    <span py:if="not value.lab_controller or not value.arch">
     System must be associated to a lab controller and have at least one architecture specified to edit install options.
    </span>
   </div>
   <div class="tab-pane" id="provision">
    <span py:if="value.lab_controller and value.arch">
     ${provision_widget.display(method='get', action=widgets_action['provision'], value=value, options=widgets_options['provision'])}
    </span>
    <span py:if="not value.lab_controller or not value.arch">
     System must be associated to a lab controller and have at least one architecture specified in order to provision.
    </span>
   </div>
   <div class="tab-pane" id="labinfo" py:if="widgets['labinfo']">
    ${widgets['labinfo'].display(method='get', action=widgets_action['labinfo'], value=value, options=widgets_options['labinfo'])}
   </div>
   <div class="tab-pane" id="history">
    ${history_widget.display(list=history_data,options=widgets_options['history'],action=widgets_action['history'])} 
   </div>
   <div class="tab-pane" id="tasks">
    ${task_widget.display(
    value=widgets_options['tasks'],
    options=widgets_options['tasks'],
    hidden=widgets_options['tasks']['hidden'],
    action=widgets_action['tasks'],
    target_dom='task_items',
    update='task_items',
    )}
    <div id="task_items">&nbsp;</div>
   </div>
    </div>
  </div>
  <script type="text/javascript">
    $(function () { link_tabs_to_anchor('beaker_system_tabs', '.system-nav'); });
  </script>
 </body>
</html>

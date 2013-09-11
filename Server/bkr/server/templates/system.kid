<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

 <head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
  <title>${title}</title>
 </head>

<body>
  <div class="page-header">
    <h1>${value.fqdn}</h1>
  </div>
  ${form.display(method='get', action=action, value=value, options=options)}
  <ul class="nav nav-tabs">
    <li><a data-toggle="tab" href="#details">Details</a></li>
    <li><a data-toggle="tab" href="#arches">Arch(s)</a></li>
    <li><a data-toggle="tab" href="#keys">Key/Values</a></li>
    <li><a data-toggle="tab" href="#groups">Groups</a></li>
    <li><a data-toggle="tab" href="#access-policy">Access Policy</a></li>
    <li><a data-toggle="tab" href="#exclude">Excluded Families</a></li>
    <li><a data-toggle="tab" href="#commands">Commands</a></li>
    <li><a data-toggle="tab" href="#power">Power Config</a></li>
    <li><a data-toggle="tab" href="#notes">Notes</a></li>
    <li><a data-toggle="tab" href="#install">Install Options</a></li>
    <li><a data-toggle="tab" href="#provision">Provision</a></li>
    <li><a data-toggle="tab" href="#labinfo">Lab Info</a></li>
    <li><a data-toggle="tab" href="#history">History</a></li>
    <li><a data-toggle="tab" href="#tasks">Tasks</a></li>
  </ul>
  <div class="tab-content">
   <div class="tab-pane" id="details">
    ${widgets['details'].display(system=value)} 
   </div>
   <div class="tab-pane" id="arches">
    ${widgets['arches'].display(method='get', action=widgets_action['arches'], value=value, options=widgets_options['arches'])} 
   </div>
   <div class="tab-pane" id="keys">
    ${widgets['keys'].display(method='get', action=widgets_action['keys'], value=value, options=widgets_options['keys'])} 
   </div>
   <div class="tab-pane" id="groups">
    ${widgets['groups'].display(method='get', action=widgets_action['groups'], value=value, options=widgets_options['groups'])}
   </div>
   <div class="tab-pane" id="access-policy">
    <div id="access-policy-${value.id}">
      <i class="icon-spinner icon-spin"/> Loading&hellip;
    </div>
    <script>
      $(function () {
        // defer until tab is shown
        $('.nav-tabs a[href="#access-policy"]').one('show', function () {
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
      <h3>Power Action</h3>
      ${widgets['power_action'].display(method='get', action=widgets_action['power_action'], value=value, options=widgets_options['power_action'])}
      <span py:if='value.lab_controller' py:strip="True">
      <h3>Netboot</h3>
      ${widgets['clear_netboot'].display(dict(fqdn=value.fqdn),
          action=tg.url('../systems/clear_netboot_form'),
          msg='Are you sure you want to clear the netboot for this system?',
           action_text='Clear Netboot', look='button')}
      </span>
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
     ${widgets['install'].display(method='get', action=widgets_action['install'], value=value, options=widgets_options['install'])} 
    </span>
    <span py:if="not value.lab_controller or not value.arch">
     System must be associated to a lab controller and have at least one architecture specified to edit install options.
    </span>
   </div>
   <div class="tab-pane" id="provision">
    <span py:if="value.lab_controller and value.arch">
     ${widgets['provision'].display(method='get', action=widgets_action['provision'], value=value, options=widgets_options['provision'])} 
    </span>
    <span py:if="not value.lab_controller or not value.arch">
     System must be associated to a lab controller and have at least one architecture specified in order to provision.
    </span>
   </div>
   <div class="tab-pane" id="labinfo">
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
  <script type="text/javascript">$(link_tabs_to_anchor);</script>
 </body>
</html>

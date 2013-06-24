<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

 <head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

  <style type="text/css" media="print">
   @import "${tg.url('/static/css/system-print.css')}";
  </style>
  <title>${title}</title>
 </head>

 <body class="flora">
  ${form.display(method='get', action=action, value=value, options=options)}
  <div class="tabber">
   <div py:if="widgets.has_key('details')" class="tabbertab"><h2>Details</h2>
    ${widgets['details'].display(system=value)} 
   </div>
   <div py:if="widgets.has_key('arches')" class="tabbertab"><h2>Arch(s)</h2>
    ${widgets['arches'].display(method='get', action=widgets_action['arches'], value=value, options=widgets_options['arches'])} 
   </div>
   <div py:if="widgets.has_key('keys')" class="tabbertab"><h2>Key/Values</h2>
    ${widgets['keys'].display(method='get', action=widgets_action['keys'], value=value, options=widgets_options['keys'])} 
   </div>
   <div py:if="widgets.has_key('groups')" class="tabbertab"><h2>Groups</h2>
    ${widgets['groups'].display(method='get', action=widgets_action['groups'], value=value, options=widgets_options['groups'])}
   </div>
   <div py:if="widgets.has_key('exclude')" class="tabbertab"><h2>Excluded Families</h2>
    <span py:if="value.lab_controller and value.arch">
     ${widgets['exclude'].display(method='get', action=widgets_action['exclude'], value=value, options=widgets_options['exclude'])} 
    </span>
    <span py:if="not value.lab_controller or not value.arch">
     System must be associated to a lab controller and have at least one architecture specified to edit exclude families.
    </span>
   </div>
   <div class="tabbertab"><h2>Commands</h2>
    <fieldset py:if="widgets.has_key('power_action')">
     <legend>Power Action</legend>
      ${widgets['power_action'].display(method='get', action=widgets_action['power_action'], value=value, options=widgets_options['power_action'])}
    </fieldset>
    <fieldset py:if='widgets.has_key("clear_netboot") and value.lab_controller'>
     <legend>Netboot</legend>
      ${widgets['clear_netboot'].display(dict(fqdn=value.fqdn),
          action=tg.url('../systems/clear_netboot_form'),
          msg='Are you sure you want to clear the netboot for this system?',
           action_text='Clear Netboot', look='button')}
    </fieldset>
    <fieldset py:if="widgets.has_key('power_history')">
     <legend>Recent Commands</legend>
     ${widgets['power_history'].display(list=widgets_options['power_history'], title='Recent Commands')}
    </fieldset>
   </div>
   <div py:if="widgets.has_key('power')" class="tabbertab"><h2>Power Config</h2>
    <fieldset py:if="not readonly">
     <legend>Power Config</legend>
     <span py:if="value.lab_controller">
      ${widgets['power'].display(method='get', action=widgets_action['power'], value=value, options=widgets_options['power'])}
     </span>
     <span py:if="not value.lab_controller">
      System must be associated to a lab controller to edit power settings.
     </span>
    </fieldset>
    <span py:if="readonly">You do not have access to edit power settings for this system.</span>
   </div>
   <div py:if="widgets.has_key('console')" class="tabbertab"><h2>Console</h2>
   </div> 
   <div py:if="widgets.has_key('notes')" class="tabbertab"><h2>Notes</h2>
    ${widgets['notes'].display(method='get', action=widgets_action['notes'], value=value, options=widgets_options['notes'])} 
   </div>
   <div py:if="widgets.has_key('install')" class="tabbertab"><h2>Install Options</h2>
    <span py:if="value.lab_controller and value.arch">
     ${widgets['install'].display(method='get', action=widgets_action['install'], value=value, options=widgets_options['install'])} 
    </span>
    <span py:if="not value.lab_controller or not value.arch">
     System must be associated to a lab controller and have at least one architecture specified to edit install options.
    </span>
   </div>
   <div py:if="widgets.has_key('provision')" class="tabbertab"><h2>Provision</h2>
    <span py:if="value.lab_controller and value.arch">
     ${widgets['provision'].display(method='get', action=widgets_action['provision'], value=value, options=widgets_options['provision'])} 
    </span>
    <span py:if="not value.lab_controller or not value.arch">
     System must be associated to a lab controller and have at least one architecture specified in order to provision.
    </span>
   </div>
   <div py:if="widgets.has_key('labinfo')" class="tabbertab"><h2>Lab Info</h2>
    ${widgets['labinfo'].display(method='get', action=widgets_action['labinfo'], value=value, options=widgets_options['labinfo'])}
   </div>
   <div py:if="locals().has_key('history_widget')" class="tabbertab"><h2>History</h2>
    ${history_widget.display(list=history_data,options=widgets_options['history'],action=widgets_action['history'])} 
   </div>
   <div py:if="locals().has_key('task_widget')" class="tabbertab"><h2>Tasks</h2>
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
 </body>
</html>

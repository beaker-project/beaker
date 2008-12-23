<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

 <head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
  <title>${title}</title>
 </head>


 <body class="flora">
  ${form.display(method='get', action=action, value=value, options=options)}
  <div class="tabber">
   <div py:if="widgets.has_key('details')" class="tabbertab"><h2>Details</h2>
    ${widgets['details'].display(system=value)} 
   </div>
   <div py:if="widgets.has_key('keys')" class="tabbertab"><h2>Key/Values</h2>
    ${widgets['keys'].display(method='get', action=widgets_action['keys'], value=value, options=widgets_options['keys'])} 
   </div>
   <div py:if="widgets.has_key('groups')" class="tabbertab"><h2>Groups</h2>
    ${widgets['groups'].display(method='get', action=widgets_action['groups'], value=value, options=widgets_options['groups'])}
   </div>
   <div py:if="widgets.has_key('exclude')" class="tabbertab"><h2>Excluded Families</h2>
    ${widgets['exclude'].display(method='get', action=widgets_action['exclude'], value=value, options=widgets_options['exclude'])} 
   </div>
   <div py:if="widgets.has_key('power')" class="tabbertab"><h2>Power</h2>
    <fieldset py:if="not readonly">
     <legend>Power Config</legend>
     ${widgets['power'].display(method='get', action=widgets_action['power'], value=value, options=widgets_options['power'])}
    </fieldset>
    <fieldset py:if="is_user">
     <legend>Power Action</legend>
      ${widgets['reboot'].display(method='get', action=widgets_action['reboot'], value=value, options=widgets_options['reboot'])}
    </fieldset>
   </div>
   <div py:if="widgets.has_key('console')" class="tabbertab"><h2>Console</h2>
   </div> 
   <div py:if="widgets.has_key('notes')" class="tabbertab"><h2>Notes</h2>
    ${widgets['notes'].display(method='get', action=widgets_action['notes'], value=value, options=widgets_options['notes'])} 
   </div>
   <div py:if="widgets.has_key('install')" class="tabbertab"><h2>Install Options</h2>
    ${widgets['install'].display(method='get', action=widgets_action['install'], value=value, options=widgets_options['install'])} 
   </div>
   <div py:if="widgets.has_key('provision')" class="tabbertab"><h2>Provision</h2>
    ${widgets['provision'].display(method='get', action=widgets_action['provision'], value=value, options=widgets_options['provision'])} 
   </div>
   <div py:if="widgets.has_key('history')" class="tabbertab"><h2>History</h2>
    ${widgets['history'].display(system=value)} 
   </div>
  </div>
 </body>
</html>

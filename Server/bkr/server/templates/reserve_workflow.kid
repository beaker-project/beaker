
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
  <body>
    <head>
    <script type='text/javascript'>
    var rw = new ReserveWorkflow("${arch.field_id}","${distro_family.field_id}","${method_.field_id}",
                                 "${tag.field_id}","${distro.field_id}","${submit.field_id}","${auto_pick.field_id}",
                                 "${arch_value}","${distro_family_value}","${tag_value}","${method_value}",
                                 [${to_json(all_arches)}],[${to_json(all_distro_familys)}],[${to_json(all_tags)}],[${to_json(all_methods)}])
    addLoadEvent(rw.initialize)
    $(document).ready(function() {
        //$("select[id!=${distro.field_id}]").change(function() { 
        //    rw.get_distros()
        //});

        $("#${auto_pick.field_id}").click(function() { 
            rw.system_available()
         })

       $("#${arch.field_id}").change(function() {
            rw.get_distros()
       })

       $("#${distro_family.field_id}").change(function() {
            var arch_value = jQuery('#'+rw.arch_id).val() 
            if (arch_value) 
                rw.get_distros()
       })

       $("#${method_.field_id}").change(function() {
            rw.get_distros()
       })

       $("#${tag.field_id}").change(function() {
            rw.get_distros()
       })
       
    })
    </script>
    </head>
    <form action="${action}" name="${name}">
      <div id="reserve_wizard" style='margin-left:3em'>
        <h3>Reserve Criteria</h3>
        <div id="arch_input">
          <label>${arch.label}</label>${arch.display()}<span id='loading' class='hidden'>&nbsp;&nbsp;&nbsp;&nbsp;</span>
        </div>

        <div id="distro_family_input"> 
          <label>${distro_family.label}</label>${distro_family.display()}<span id='loading' class='hidden'>&nbsp;&nbsp;&nbsp;&nbsp;</span>
        </div>
        
        <div id="method_input">
          <label>${method_.label}</label>${method_.display()}<span id='loading' class='hidden'>&nbsp;&nbsp;&nbsp;&nbsp;</span>
        </div>

        <div id="tag_input">
          <label>${tag.label}</label>${tag.display()}<span id='loading' class='hidden'>&nbsp;&nbsp;&nbsp;&nbsp;</span>
        </div>
      </div>

     
      <div style="margin-left:3em">
        <h3>Select Distro</h3>     
          <label>${distro.label}</label> ${distro.display()}<span id='loading' class='hidden'>&nbsp;&nbsp;&nbsp;&nbsp;</span>
      </div>
     <br /><br />
     ${submit.display()} 

     ${auto_pick.display()}&nbsp;<warn id="reserve_error" class="rounded-side-pad" style='display:none'>No Systems compatible for that distro</warn> 
    </form>
  </body>
</html>

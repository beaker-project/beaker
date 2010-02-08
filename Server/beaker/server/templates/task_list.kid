<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#">
  <body>
    <head>
    <script type='text/javascript'>
    $(document).ready(function() {
      $("a[id ^= 'show_rpm_table']").click(function() {
        id = $(this).attr('id')
        my_regex = /^show_rpm_table_(\d{1,})/
        number = id.replace(my_regex,"$1")
        $('#rpm_table_'+number).toggle() 
      });

      $("a[id ^= 'show_results_table']").click(function() {
        id = $(this).attr('id')
        my_regex = /^show_results_table_(\d{1,})/
        number = id.replace(my_regex,"$1")
        $('#results_table_'+number).toggle()
      });
    });
    </script>
    </head>
    <span py:if="tg.paginate.href_prev">
        <a href="${tg.paginate.href_first}">&lt;&lt;</a>
        <a href="${tg.paginate.href_prev}">&lt;</a>
    </span>
    <span py:if="tg.paginate.page_count > 1" py:for="page in tg.paginate.pages">
      <span py:if="page == tg.paginate.current_page" py:replace="page"/>
      <span py:if="page != tg.paginate.current_page">
         <a href="${tg.paginate.get_href(page)}">${page}</a>
      </span>
    </span>

    <span py:if="tg.paginate.href_next">
      <a href="${tg.paginate.href_next}">&gt;</a>
      <a href="${tg.paginate.href_last}">&gt;&gt;</a>
    </span>
    <table py:for=" i,(d, rpm, result) in enumerate(data)" id='outer_table'>
      <thead>
        <tr>
          <th>Job</th>
          <th>Recipe</th>
          <th>Task</th>
          <th>Start</th>
          <th>Duration</th>
          <th>Status</th>
        </tr>
      </thead>
     <tbody>
       <tr>
         <td>${d.job_id}</td>
         <td>${d.recipe_id}</td>
         <td>${d.task_name}</td>  
         <td>${d.start_time}</td>          
         <td py:if="d.status == 'Completed'">${d.duration}</td>
         <td py:if="d.status != 'Completed'"> N/A </td>
         <td>${d.status}</td>
       </tr>
       <tr>
         <td class='sub_head'>Family</td>
         <td class='sub_head'>Tree</td>
         <td class='sub_head'>System</td>
         <td class='sub_head'>Arch</td>
       </tr> 
       <tr> 
         <td>fam</td>
         <td>${d.distro_name}-${d.variant}</td>
         <td>${d.system_name}</td>
         <td>${d.arch}</td>
       </tr>
     <tr>
       <td colspan="6" class="toggle_link">
         <a class="rounded-side-pad" id="show_rpm_table_${i}">Toggle RPM details</a>  
       </td>
     </tr>
     <tr>
        <td colspan="6">  
          <span py:if="not rpm.all()">
            <info id="rpm_table_${i}" >
              No RPM data found 
            </info>
          </span>
          <table class="inner_table" id="rpm_table_${i}" py:for="r in rpm"> 
            <thead>
              <tr>
                <th>Package</th>
                <th>Version</th>
                <th>Release</th>
                <th>Arch</th>
              </tr>
            </thead> 
            <tbody>
              <tr>
                <td>${r.package}</td>
                <td>${r.version}</td>
                <td>${r.release}</td>
                <td>${r.arch}</td>
              </tr>
            </tbody>
          </table>
          </td>
         </tr>    
         <tr>
           <td colspan="6" class="toggle_link">
             <a class="rounded-side-pad" id="show_results_table_${i}">Toggle Result details</a>  
           </td>
         </tr>
         <tr>  
           <td colspan="6">  
             <span py:if="not result.all()">
               <info id="rpm_table_${i}" >
                 No result data found 
               </info>
             </span>
             <table py:if="result" class='inner_table' id="results_table_${i}">
               <thead>
                 <tr>
                   <th style='width:14em'>Task</th>
                   <th>Result</th>
                   <th>Packages</th>
                 </tr>
               </thead>
               <tbody>
                 <tr py:for="re in result">
                   <td>${re.path}</td>
                   <td>${re.result}</td>
                   <td>none</td>
                 </tr>
               </tbody>
             </table>   
           </td>
         </tr>
     </tbody>
    </table>
  </body>
</html>

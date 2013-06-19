<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">

 <head>
  <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>

  <title>CSV Import Results</title>
 </head>

 <body class="flora">
   <table class="list" id="csv-import-log">
    <tr class="list">
     <th class="list">Error Log</th>
    </tr>
    <?python row_color = "#FFFFFF" ?>
    <tr class="list" bgcolor="${row_color}" py:if="not log">
     <td class="list">No Errors</td>
    </tr>
    <tr class="list" bgcolor="${row_color}" py:for="line in log">
     <td class="list">${line}</td>
     <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
    </tr>
   </table>
 </body>
</html>

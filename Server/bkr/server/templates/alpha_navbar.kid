<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<div xmlns:py="http://purl.org/kid/ns#"
 style="padding-top:0.5em;text-align:center">
  <a py:for="letter in sorted(letters)" 
   style="padding:0 0.2em 0 0.2em;font-size:2em" 
   href="?${keyword}.text.starts_with=${letter}">
    ${letter}
  </a>
</div>

<div xmlns:py="http://purl.org/kid/ns#">
<script type='text/javascript'>
  pri = new Priority("${field_id}","${controller}")
  pri.initialize()

  $(document).ready(function() {
      $("#${field_id}").change(function() {
          pri.changePriority($("#${field_id}").val())
      })

  })
</script>
<select
    name="${name}"
    class="${field_class}"
    id="${field_id}"
    py:attrs="attrs"
>
    <optgroup py:for="group, options in grouped_options"
        label="${group}"
        py:strip="not group"
    >
        <option py:for="value, desc, attrs in options"
            value="${value}"
            py:attrs="attrs"
            py:content="desc"
        />
    </optgroup>
</select>
</div>

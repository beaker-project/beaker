<html xmlns:py="http://purl.org/kid/ns#"> 
<button py:if="submit" onclick="document.theForm.submit();" class="button" name="${name}" value="${value}"> ${button_label} </button>
<button py:if="not submit" class="button" name="${name}" value="${value}"> ${button_label} </button>
</html>

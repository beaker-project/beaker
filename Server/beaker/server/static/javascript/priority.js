Priority = function(priority_field,controller) {
    this.priority_field = priority_field
    this.controller = controller
}


Priority.prototype.changePriority = function(priority) {
    var params = {"tg_format" : "json",
                  "tg_random" : new Date().getTime(),
                  "priority" : priority }
    alert(priority)
    var d = loadJSONDoc(self.controller + "?" + queryString(params))
    d.addCallback(this.priorityChanged)
}

Priority.prototype.priorityChanged = function() {
   
}

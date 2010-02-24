PriorityManager = function () {
    this.field_type = {}
    this.controllers = {'recipeset' : this.RecipeSetChanged}
    this.my_regex = /^.+?(\d{1,})$/
}

PriorityManager.prototype.initialize = function() {
    bindMethods(this)
}

PriorityManager.prototype.register = function(id,type) {
    this.field_type[id] = type
}

PriorityManager.prototype.changePriority = function(elem_id,new_val) {
   
    var type = this.field_type[elem_id]
    id = elem_id.replace(this.my_regex,"$1") 
    if (type) {
        controller = this.controllers[type]
        if (controller) {
            alert('calling register with priorty ' + new_val)
            controller(new_val,id,1)    
        }
    }  
}

PriorityManager.prototype.RecipeSetChanged = function(new_priority_id,recipeset_id,parent_) { 
    var params = {"tg_format" : "json",
                  "tg_random" : new Date().getTime(),
                  "priority_id" : new_priority_id,
                  "recipeset_id" : recipeset_id }
  
    var d = loadJSONDoc('/change_priority_recipeset' + "?" + queryString(params))
    d.addCallback(this.priorityChanged)
}

PriorityManager.prototype.priorityChanged = function(result) {
  
}

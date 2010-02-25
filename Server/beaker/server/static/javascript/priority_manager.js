PriorityManager = function () {
    this.field_type = {}
    this.controllers = {'recipeset' : PriorityManager.prototype.RecipeSetChanged,'parent' : PriorityManager.prototype.ChangeAll}
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
            controller(new_val,id)    
        }
    }  
}

PriorityManager.prototype.RecipeSetChanged = function(new_priority_id,recipeset_id) { 
    var params = {"tg_format" : "json",
                  "tg_random" : new Date().getTime(),
                  "priority_id" : new_priority_id,
                  "recipeset_id" : recipeset_id }
  
    var d = loadJSONDoc('/change_priority_recipeset' + "?" + queryString(params))
    d.addCallback(PriorityManager.prototype.priorityChanged)
}

PriorityManager.prototype.ChangeAll = function(new_priority_id,job_id) { 
    for (i in this.pri_manager.field_type) {
        var type = this.pri_manager.field_type[i]
        if (type != 'parent') {
            var f = this.pri_manager.controllers[type]    
            var id = i.replace(this.pri_manager.my_regex,"$1") 
            f(new_priority_id,id) 
            $('#'+i).val(new_priority_id)
            //replaceChildNodes(this.i, map(this.replacePriority ,this.all_arches))
        }
    }
}

PriorityManager.prototype.priorityChanged = function(result) { 
   
}  






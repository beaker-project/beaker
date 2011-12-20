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

PriorityManager.prototype.changePriority = function(elem_id,new_val,callback) { 
    var type = this.field_type[elem_id]
    id = elem_id.replace(this.my_regex,"$1") 
    if (type) {
        controller = this.controllers[type]
        if (controller) {          
            controller(new_val,id,callback)    
        }
    }  
}

PriorityManager.prototype.RecipeSetChanged = function(new_priority, recipeset_id, callback) {
    var params = {"tg_format" : "json",
                  "tg_random" : new Date().getTime(),
                  "priority" : new_priority,
                  "recipeset_id" : recipeset_id }
    AjaxLoader.prototype.add_loader('priority_recipeset_' + recipeset_id) 
    var d = loadJSONDoc('../change_priority_recipeset' + "?" + queryString(params))
    // I wish we could just pass the callback var to priorityChanged
    // Reason we can't is because it each call uses the same pointer value it seems! 
    d.addCallback(PriorityManager.prototype.priorityChanged,callback['function'],callback['args']['element_id'],callback['args']['value']) //mochikit's built in currying...
}

PriorityManager.prototype.ChangeAll = function(new_priority, job_id, callback) {
    for (i in this.pri_manager.field_type) {
        var type = this.pri_manager.field_type[i]
        if (type != 'parent') { 
            var f = this.pri_manager.controllers[type]    
            var id = i.replace(this.pri_manager.my_regex,"$1") 
            callback['args']['element_id'] = i  
            f(new_priority, id, callback);
            //replaceChildNodes(this.i, map(this.replacePriority ,this.all_arches))
        }
    }
}

PriorityManager.prototype.priorityChanged = function(f,elem_id,value,result) {  
    AjaxLoader.prototype.remove_loader(elem_id)
    f(elem_id,value,result['current_priority'],result['msg'],result['success']) 
}  






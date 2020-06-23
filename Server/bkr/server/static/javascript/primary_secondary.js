PrimarySecondary = function () {
    this.field_type = {}
    this.controllers = {} 
    this.change_value_controller = null //This needs to be set as the server side controller for changing the value

    //FIXME This should be inherited instead of in here
    this.my_regex = null
}


PrimarySecondary.prototype.initialize = function() {
    bindMethods(this)
}

PrimarySecondary.prototype.register = function(id,type) {
    this.field_type[id] = type
}

PrimarySecondary.prototype.changeValue = function(elem_id,new_val,callback) { 
    var type = this.field_type[elem_id]
    id = elem_id.replace(this.my_regex,"$1") //#FIXME see comment above about moving this regex.
    if (type) {
        controller = this.controllers[type](this)
        if (controller) {          
            controller(new_val,id,callback)    
        }
    }  
}

PrimarySecondary.prototype.SecondaryChanged = function(new_value_id,secondary_id,callback) {
    var params = {"tg_format" : "json",
                  "tg_random" : new Date().getTime(),
                  "value_id" : new_value_id,
                  "secondary_id" : secondary_id }
  
    var d = loadJSONDoc(this.change_value_controller + "?" + queryString(params))
    // I wish we could just pass the callback var to valueChanged
    // Reason we can't is because it each call uses the same pointer value it seems! 
    d.addCallback(PrimarySecondary.prototype.valueChanged,callback['function'],callback['args']['element_id'],callback['args']['value']) //mochikit's built in currying...
}



PrimarySecondary.prototype.valueChanged = function(f,elem_id,value,result) {  
    AjaxLoader.prototype.remove_loader(elem_id)
    f(elem_id,value,result['current_value'],result['msg'],result['success']) 
}  


PrimarySecondary.prototype.ChangeAll = function(new_value_id,primary_id,callback) {
    for (i in this.field_type) { //FIXME all this was pri_manager before, does it work?
        var type = this.field_type[i]
        if (type == 'secondary') {
            var f = this.controllers[type](this) //Closure    
            var id = i.replace(this.my_regex,"$1") 
            callback['args']['element_id'] = i  
            f(new_value_id,id,callback) 
            //replaceChildNodes(this.i, map(this.replacePriority ,this.all_arches))
        }
    }
}

SearchObject = function() {
}

SearchObject.prototype.initialize = function(data) {
    if (SearchObject.prototype.the_instance != null) {
        return SearchObject.prototype.the_instance
    }

    lowered_data = Object()
    for (i in data) {
        lowered_data[i.toLowerCase()] = data[i]
    }
    SearchObject.prototype.the_instance = this
    SearchObject.prototype.data = lowered_data;   
}

SearchObject.prototype.table_value = function(table_value) {
    try {
        return SearchObject.prototype.data[table_value] 
    } catch (err) {
        return null;
    }    
}

SearchObject.prototype.keyvalue_value = function(keyvalue) {
    try {
        data = SearchObject.prototype.table_value('key/value')
        return data[keyvalue]
    } catch (err) {
        return null
    }
}

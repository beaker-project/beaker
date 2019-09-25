function toggleExcludeAll(){
    var major = $(".majorCheckbox");
    major[0].checked = !major[0].checked;
    for(var i = 1; i < major.length; i++){
        major[i].checked = major[0].checked;
        major[i].indeterminate = false;
    }
}

function toggleExclude(arch, value){
    searchString = arch;
    if(value){
        searchString += ("_" +value);
    }
    var major = $("[id*="+searchString+"].majorCheckbox:not(.filtered-out)");
    major[0].checked = !major[0].checked;
    for(var i = 1; i < major.length; i++){
        major[i].checked = major[0].checked;
        checkMajor(major[i]);
        major[i].indeterminate = false;
    }
}

function filterFamilies(filterString){
    var labels = $(".excludedfamilies label");
    for(var i=0; i<labels.length;i++){
        if(labels[i].children[1].innerHTML.toLowerCase().search(filterString.toLowerCase()) == -1){
            labels[i].parentElement.style.display = "none";
            labels[i].children[0].classList.add("filtered-out");
        }
        else{
            labels[i].parentElement.style.display = "";
            labels[i].children[0].classList.remove("filtered-out");
        }
    }
}

function preventSubmit(event){
    if(event.key == "Enter"){
        event.preventDefault();
    }
}

function _findParentElement(element, parentTag){
    if(element.parentNode.tagName == parentTag){
        return element.parentNode;
    }
    return _findParentElement(element.parentNode, parentTag);
}

function checkMajor(checkBox){
    if(checkBox.checked){
        var parentDiv = _findParentElement(checkBox, "DIV");
        var versions = parentDiv.querySelectorAll("input:not(.majorCheckbox)");
        for(var i=0; i<versions.length; i++){
            versions[i].checked = false;
        }
    }
}

function checkVersion(checkBox){
    var parentDiv = _findParentElement(checkBox, "DIV");
    var major = parentDiv.querySelector("input.majorCheckbox");
    var versions = parentDiv.querySelectorAll("input:not(.majorCheckbox)");
    if(checkBox.checked){
        major.checked = false;
        major.indeterminate = true;
    }
    else{
        for(var i=0; i<versions.length; i++){
            if(versions[i].checked){
                return;
            }
        }
        major.indeterminate = false;
    }
}

function initializeExcludedFamilies(){
    var majors = document.querySelector(".archs-list").querySelectorAll("input.majorCheckbox");
    var versions = document.querySelector(".archs-list").querySelectorAll("input:not(.majorCheckbox)");
    for(var i=0; i<majors.length; i++){
        checkMajor(majors[i]);
    }
    for(var i=0; i<versions.length; i++){
        checkVersion(versions[i]);
    }

    $('.nav-tabs li:first-child a').tab('show');
}

function backToTop(){
    document.body.scrollTop = 0;
    document.documentElement.scrollTop = 0;
}

function backToTopShow(event){
    if(event.target.URL.search("#exclude") != -1){
        if (document.body.scrollTop > 350 || document.documentElement.scrollTop > 350) {
            document.querySelector(".back-to-top").style.display = "block";
        } else {
            document.querySelector(".back-to-top").style.display = "";
        }
    }
}

window.addEventListener("scroll", backToTopShow);
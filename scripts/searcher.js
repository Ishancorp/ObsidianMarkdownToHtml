function searchForArticle() {
    // Declare variables
    // var input, filter, ul, li, a, i, txtValue;
    pane = document.getElementById("searchbar");
    input = pane.querySelector('#searchInput');
    filter = input.value.toLowerCase().replace(/\s+/g, '-');
    ul = pane.querySelector("#articles");
    li = ul.getElementsByTagName('li');

    // Loop through all list items, and hide those who don't match the search query
    for (i = 0; i < li.length; i++) {
        a = li[i].getElementsByTagName("a")[0];
        searchText = a.getAttribute("searchText");
        txtValue = a.textContent || a.innerText;
        if (txtValue.toLowerCase().replace(/\s+/g, '-').indexOf(filter) > -1 
            || 
            searchText.toLowerCase().replace(/\s+/g, '-').indexOf(filter) > -1) {
            li[i].style.display = "";
        } else {
            li[i].style.display = "none";
        }
    }
}
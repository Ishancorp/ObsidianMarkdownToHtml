function searchForArticle() {
    const pane = document.getElementById("searchbar");
    const input = pane.querySelector('#searchInput');
    const query = input.value.trim().toLowerCase();
    const terms = query.split(/\s+/); // split on spaces (multiple spaces collapsed)
    
    const checkbox = document.getElementById('toggleByText');
    
    const ul = pane.querySelector("#articles");
    const liElements = ul.getElementsByTagName('li');

    for (const li of liElements) {
        const a = li.querySelector("a");
        const searchText = (a.getAttribute("searchText") || "").toLowerCase();
        const searchID = a.getAttribute("searchID");
        const txtValue = (a.textContent || a.innerText).toLowerCase();

        // Combine searchable text
        let combined = `${txtValue} ${searchText}`;
        if(checkbox.checked){
            combined = fileContents[searchID].toLowerCase();
            if(searchText.endsWith(".base.html") || !searchText.endsWith(".html")){
                combined = ""
            }
        }

        // Show only if ALL search terms are found
        const matches = terms.every(term => combined.includes(term));

        li.style.display = matches ? "" : "none";
    }
}

function updatePlaceholder() {
    const input = document.getElementById('searchInput');
    const checkbox = document.getElementById('toggleByText');
    
    if(checkbox.checked) {
        input.placeholder = "Search by content";
    } else {
        input.placeholder = "Search by name";
    }
}

function searchForArticle() {
    const pane = document.getElementById("searchbar");
    const input = pane.querySelector('#searchInput');
    const query = input.value.trim().toLowerCase();
    const terms = query.split(/\s+/); // split on spaces (multiple spaces collapsed)
    
    const ul = pane.querySelector("#articles");
    const liElements = ul.getElementsByTagName('li');

    for (const li of liElements) {
        const a = li.querySelector("a");
        const searchText = (a.getAttribute("searchText") || "").toLowerCase();
        const txtValue = (a.textContent || a.innerText).toLowerCase();

        // Combine searchable text
        const combined = `${txtValue} ${searchText}`;

        // Show only if ALL search terms are found
        const matches = terms.every(term => combined.includes(term));

        li.style.display = matches ? "" : "none";
    }
}

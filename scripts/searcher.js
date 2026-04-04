function searchForArticle() {
    const pane = document.getElementById("searchbar");
    const input = pane.querySelector('#searchInput');
    const query = input.value.trim();
    
    const ul = pane.querySelector("#articles");
    const liElements = ul.getElementsByTagName('li');
    
    if(!query) {
        for (const li of liElements) {
            li.style.display = "";
            const existingSnippet = li.querySelector('.content-snippet');
            if(existingSnippet) existingSnippet.remove();
        }
        return;
    }
    
    const queryLower = normalize(query);
    const checkbox = document.getElementById('toggleByText');

    for (const li of liElements) {
        const a = li.querySelector("a");
        const searchText = normalize(a.getAttribute("searchText") || "");
        const searchID = a.getAttribute("searchID");
        const txtValue = normalize(a.textContent || a.innerText);

        let matches = false;
        let contentPreview = "";
        
        if(checkbox.checked){
            const fullContent = fileContents[searchID];
            
            if(!searchText.endsWith(".base.html") && searchText.endsWith(".html") && fullContent) {
                const lines = fullContent.split('\n');
                for(let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    
                    if(normalize(line).includes(queryLower)) {
                        matches = true;
                        contentPreview = generateSnippetFromLine(line, query);
                        break;
                    }
                }
            }
        } else {
            const combined = `${txtValue} ${searchText}`;
            matches = combined.includes(queryLower);
        }

        li.style.display = matches ? "" : "none";
        
        const existingSnippet = li.querySelector('.content-snippet');
        if(matches && checkbox.checked && contentPreview) {
            if(existingSnippet) {
                existingSnippet.innerHTML = contentPreview;
            } else {
                const snippetDiv = document.createElement('div');
                snippetDiv.className = 'content-snippet';
                snippetDiv.innerHTML = contentPreview;
                a.appendChild(snippetDiv);
            }
        } else if(existingSnippet) {
            existingSnippet.remove();
        }
    }
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function normalize(string) {
    return string.toLowerCase()
                 .replace(/[\u201C\u201D\u201E\u201F\u275D\u275E]/g, '"')
                 .replace(/[\u2018\u2019\u201A\u201B\u275B\u275C]/g, "'");
}

function generateSnippetFromLine(line, searchTerm) {
    let snippet = line.trim();
    const searchTermLower = normalize(searchTerm);
    const snippetLower = normalize(snippet);
    const pos = snippetLower.indexOf(searchTermLower);
    
    if(pos === -1) return "";
    
    const maxLength = 120;
    if(snippet.length > maxLength) {
        const contextLength = 60;
        const start = Math.max(0, pos - contextLength);
        const end = Math.min(snippet.length, pos + searchTerm.length + contextLength);
        
        snippet = snippet.substring(start, end);
        if(start > 0) snippet = "..." + snippet;
        if(end < line.trim().length) snippet = snippet + "...";
    }
    
    const escapedTerm = escapeRegex(searchTerm);
    const regex = new RegExp(escapedTerm, 'gi');
    snippet = snippet.replace(regex, '<mark>$&</mark>');
    
    return `<sub class="content-preview">${snippet}</sub>`;
}

function updatePlaceholder() {
    const input = document.getElementById('searchInput');
    const checkbox = document.getElementById('toggleByText');
    
    if(checkbox.checked) {
        input.placeholder = "Search by content";
    } else {
        input.placeholder = "Search by name";
    }
    
    searchForArticle();
}

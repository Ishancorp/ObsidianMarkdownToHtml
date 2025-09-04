// Note: This file CANNOT be run in this state. It must be processed first, plopping in relevant content in these four consts here. 

const fileLinks = {/*file_links*/}
const fileContentMap = {/*file_content_map*/}
const fileContents = {/*file_contents*/}
const inDirectory = /*in_directory*/0
const outDirectory = /*out_directory*/0

// Client-side Obsidian processor with transclusions
// Fixed version of the ObsidianProcessor with corrected transclusion logic

function getFile(id){
    return fileContents[fileContentMap[id]];
}

class ObsidianProcessor {
    constructor() {
        this.image_types = new Set(['png', 'svg', 'jpg', 'jpeg', 'gif', 'webp']);
        this.transclusion_depth = 0;
        this.max_transclusion_depth = 5;
        this.processing_files = new Set();
    }

    async processMarkdown(content, currentFile = null) {
        content = this.fixTableSpacing(content);
        
        // Handle transclusions first (before other processing)
        content = await this.processTransclusions(content, currentFile);
        
        // Handle wikilinks
        content = this.processWikilinks(content);
        
        // Handle footnotes
        content = this.processFootnotes(content);
        
        // Handle block references
        content = this.processBlockReferences(content);
        
        return content;
    }

    unescapeHtml(text) {
        return text
            .replace(/&amp;/g, "&")
            .replace(/&lt;/g, "<")
            .replace(/&gt;/g, ">")
            .replace(/&quot;/g, '"')
            .replace(/&#x27;/g, "'");
    }

    // Process canvas nodes specifically
    async processCanvasNodes() {
        document.getElementById('rendered-content').innerHTML = this.unescapeHtml(document.getElementById('markdown-content').innerHTML)
        const nodeContents = document.querySelectorAll('.general-boxes');
        console.log(`Found ${nodeContents.length} canvas nodes to process`);
        
        for (let i = 0; i < nodeContents.length; i++) {
            const nodeContent = nodeContents[i];
            const rawMarkdown = nodeContent.innerHTML;
            const renderedDiv = nodeContent;
            
            console.log(`Processing node ${i + 1}/${nodeContents.length}`);
            
            if (!rawMarkdown) {
                console.warn(`Node ${i + 1}: No markdown data found`);
                if (renderedDiv) renderedDiv.innerHTML = '<p>No content</p>';
                continue;
            }
            
            if (!renderedDiv) {
                console.warn(`Node ${i + 1}: No rendered div found`);
                continue;
            }
            
            try {
                // Unescape the HTML-escaped markdown
                const unescapedMarkdown = this.unescapeHtml(rawMarkdown);
                console.log(`Node ${i + 1} raw content:`, unescapedMarkdown.substring(0, 100) + '...');
                
                // Process the markdown through our pipeline
                const processedContent = await this.processMarkdown(unescapedMarkdown);
                console.log(`Node ${i + 1} processed content:`, processedContent.substring(0, 100) + '...');
                
                const htmlContent = marked.parse(processedContent);
                
                // Apply post-processing for spacing
                const spacedContent = htmlContent.replace(/<\/p>\s*<p>/g, '</p><br><p>');
                
                renderedDiv.innerHTML = spacedContent;
                console.log(`Node ${i + 1}: Successfully rendered`);
                
            } catch (error) {
                console.error(`Error processing canvas node ${i + 1}:`, error);
                console.error(`Node content was:`, rawMarkdown);
                renderedDiv.innerHTML = `<p>Error processing content: ${error.message}</p>`;
            }
        }
        
        // Re-render MathJax for any new mathematical content
        if (typeof MathJax !== 'undefined' && MathJax.typesetPromise) {
            try {
                await MathJax.typesetPromise();
                console.log('MathJax re-rendered for canvas nodes');
            } catch (error) {
                console.warn('MathJax rendering error:', error);
            }
        }
    }

    async processTransclusions(content, currentFile = null) {
        if (this.transclusion_depth >= this.max_transclusion_depth) {
            console.log('Max transclusion depth reached');
            return content;
        }

        this.transclusion_depth++;

        // Pattern for transclusions: ![[filename]] or ![[filename#section]]
        const transclusion_pattern = /!\[\[([^\]]+)\]\]/g;
        
        const matches = [...content.matchAll(transclusion_pattern)];
        console.log(`Found ${matches.length} transclusion(s) to process`);

        let processedContent = content;
        let totalOffset = 0;

        // Process each transclusion in order
        for (const match of matches) {
            const fullMatch = match[0];
            const link = match[1];
            const matchStart = match.index + totalOffset;
            const matchEnd = matchStart + fullMatch.length;

            console.log(`Processing transclusion: ${link}`);
            const replacement = await this.processTransclusion(link, currentFile);
            
            // Replace in the content
            const before = processedContent.substring(0, matchStart);
            const after = processedContent.substring(matchEnd);
            processedContent = before + replacement + after;

            // Adjust offset for next iteration
            totalOffset += replacement.length - fullMatch.length;
        }

        this.transclusion_depth--;
        return processedContent;
    }

    generateTransclusionId(fileName) {
        // Create a simple hash-like ID from filename and timestamp
        const timestamp = Date.now().toString(36);
        const nameHash = fileName.replace(/[^a-zA-Z0-9]/g, '').substring(0, 8);
        return `transcl-${nameHash}-${timestamp}`;
    }

    processTransclusionFootnotes(content, fileName) {
        const footnotes = {};
        let footnoteCounter = 1;
        const transclusionId = this.generateTransclusionId(fileName);

        // Extract footnote definitions
        let contentWithoutFootnotes = content.replace(/^\[\^([^\]]+)\]:\s*(.*)$/gm, (match, id, text) => {
            footnotes[id] = text;
            return '';
        });

        // Replace footnote references with transclusion-specific IDs
        contentWithoutFootnotes = contentWithoutFootnotes.replace(/\[\^([^\]]+)\]/g, (match, id) => {
            if (footnotes.hasOwnProperty(id)) {
                const uniqueId = `${transclusionId}-${id}`;
                const tooltipContent = this.escapeTooltipContent(footnotes[id]);
                footnoteCounter++;
                return `<span class="fn"><a href="#fn-${uniqueId}" class="fn-link" id="fnref-${uniqueId}"><sup>[${id}]</sup></a><span class="fn-tooltip">${tooltipContent}</span></span>`;
            }
            return match;
        });

        // Generate footnotes HTML if any exist
        let footnotesHtml = '';
        if (Object.keys(footnotes).length > 0) {
            footnotesHtml = '<div class="transclusion-footnotes"><hr class="footnote-separator"><ol class="footnote-list">';
            for (const [id, text] of Object.entries(footnotes)) {
                const uniqueId = `${transclusionId}-${id}`;
                footnotesHtml += `<li id="fn-${uniqueId}">${text} <a href="#fnref-${uniqueId}" class="footnote-backref">↩</a></li>`;
            }
            footnotesHtml += '</ol></div>';
        }

        return {
            content: contentWithoutFootnotes,
            footnotesHtml: footnotesHtml
        };
    }

    async processTransclusion(link, currentFile) {
        console.log('Processing transclusion:', link);

        // Check if it's an image
        if (link.includes('.')) {
            const extension = link.split('.').pop().toLowerCase();
            if (this.image_types.has(extension)) {
                return this.processImageTransclusion(link);
            }
        }

        // Parse the link for file and section
        let fileName, section;
        if (link.includes('#')) {
            [fileName, section] = link.split('#', 2);
        } else {
            fileName = link;
            section = null;
        }

        // Find file content
        let originalFileContent = this.findFileContent(fileName);
        if (!originalFileContent) {
            console.log('File not found:', fileName);
            return `> File not found: ${link}`;
        }

        // Prevent circular references
        if (this.processing_files.has(fileName)) {
            console.log('Circular reference detected:', fileName);
            return `> Circular reference detected: ${link}`;
        }

        this.processing_files.add(fileName);

        let fileContent;
        // Extract section if specified
        if (section) {
            fileContent = this.extractSectionWithFootnotes(originalFileContent, section);
            if (!fileContent) {
                console.log('Section not found:', section, 'in file:', fileName);
                this.processing_files.delete(fileName);
                return `> Section not found: ${link}`;
            }
        } else {
            fileContent = originalFileContent;
        }

        // Process footnotes WITHIN this transclusion
        const { content: contentWithoutFootnotes, footnotesHtml } = this.processTransclusionFootnotes(fileContent, fileName);

        // Recursively process transclusions in the transcluded content
        const processedContent = await this.processTransclusions(contentWithoutFootnotes, fileName);

        this.processing_files.delete(fileName);

        // Format as blockquote with source link
        const lines = processedContent.split('\n');
        const blockquote = lines.map(line => line.trim() ? `> ${line}` : '>').join('\n');

        // Create the transclusion display
        let result = `\n\n> <span class="transcl-bar"><span>${section ? `**${fileName}** <span class="file-link">></span> **${section}**` : `**${fileName}**`}</span> <span class="goto">[[${link}|>>]]</span></span>\n>\n${blockquote}`;

        // Add footnotes at the bottom of this transclusion if they exist
        if (footnotesHtml) {
            result += `\n>\n> ${footnotesHtml.replace(/\n/g, '\n> ')}`;
        }

        result += '\n\n';

        return result;
    }

    processImageTransclusion(imageLink) {
        const imgHref = this.getLinkHref(imageLink);
        if (imgHref !== '#file-not-found') {
            return `<img src="${imgHref}" alt="${imageLink}" />`;
        }
        return `<span class="broken-link">![[${imageLink}]]</span>`;
    }

    findFileContent(fileName) {
        console.log('Looking for file content:', fileName);
        console.log('Available files:', Object.keys(fileContents));
        
        // Try exact match first
        if (fileContentMap.hasOwnProperty(fileName)) {
            console.log('Found exact match:', fileName);
            return getFile(fileName);
        }
        
        // Try with .md extension
        if (fileContentMap.hasOwnProperty(fileName + '.md')) {
            console.log('Found with .md extension:', fileName + '.md');
            return getFile(fileName + '.md');
        }

        // Try case-insensitive match
        const lowerFileName = fileName.toLowerCase();
        for (const [key, content] of Object.entries(fileContentMap)) {
            if (key.toLowerCase() === lowerFileName || key.toLowerCase() === lowerFileName + '.md') {
                console.log('Found case-insensitive match:', key);
                return fileContents[content];
            }
        }

        // Try basename match (last resort)
        const baseName = fileName.split('/').pop().split('\\').pop();
        const matches = Object.keys(fileContents).filter(k => {
            const keyBase = k.split('/').pop().split('\\').pop();
            return keyBase === baseName || keyBase === baseName + '.md';
        });
        
        if (matches.length === 1) {
            console.log('Found basename match:', matches[0]);
            return getFile(matches[0]);
        } else if (matches.length > 1) {
            console.log('Multiple basename matches found, using first:', matches[0]);
            return getFile(matches[0]);
        }

        console.log('File not found:', fileName);
        return null;
    }

    extractSectionWithFootnotes(fullContent, sectionName) {
        console.log('Extracting section with footnotes:', sectionName);

        // Handle block references (^blockid)
        if (sectionName.startsWith('^')) {
            const blockId = sectionName.substring(1);
            const blockContent = this.extractBlockContent(fullContent, blockId);
            if (blockContent) {
                return this.collectFootnotesForContent(blockContent, fullContent);
            }
            return null;
        }

        // Handle regular header sections
        const sectionContent = this.extractSection(fullContent, sectionName);
        if (!sectionContent) {
            return null;
        }

        // Collect footnotes referenced in this section
        return this.collectFootnotesForContent(sectionContent, fullContent);
    }

    collectFootnotesForContent(content, fullContent) {
        // Find all footnote references in the section content
        const footnoteRefs = new Set();
        const refMatches = content.matchAll(/\[\^([^\]]+)\]/g);

        for (const match of refMatches) {
            footnoteRefs.add(match[1]);
        }

        if (footnoteRefs.size === 0) {
            return content;
        }

        // Extract footnote definitions from the full file content
        const footnoteDefinitions = [];
        const lines = fullContent.split('\n');

        for (const line of lines) {
            const defMatch = line.match(/^\[\^([^\]]+)\]:\s*(.*)$/);
            if (defMatch) {
                const [, id, text] = defMatch;
                if (footnoteRefs.has(id)) {
                    footnoteDefinitions.push(line);
                }
            }
        }

        // Combine section content with its footnote definitions
        if (footnoteDefinitions.length > 0) {
            return content + '\n\n' + footnoteDefinitions.join('\n');
        }

        return content;
    }

    extractSection(content, sectionName) {
        console.log('Extracting section:', sectionName);

        // Handle block references (^blockid)
        if (sectionName.startsWith('^')) {
            const blockId = sectionName.substring(1);
            return this.extractBlockContent(content, blockId);
        }

        // Handle regular header sections
        const lines = content.split('\n');
        const sectionLines = [];
        let inSection = false;
        let sectionLevel = 0;

        const sectionSlug = this.slugify(sectionName);
        console.log('Looking for section slug:', sectionSlug);

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.trim().startsWith('#')) {
                const headerMatch = line.match(/^(#+)\s*(.*)$/);
                if (headerMatch) {
                    const currentLevel = headerMatch[1].length;
                    const currentHeader = headerMatch[2].trim();
                    const currentSlug = this.slugify(currentHeader);

                    console.log(`Found header: "${currentHeader}" (slug: "${currentSlug}") at level ${currentLevel}`);

                    if (currentSlug === sectionSlug || currentHeader.toLowerCase() === sectionName.toLowerCase()) {
                        console.log('Section found!');
                        inSection = true;
                        sectionLevel = currentLevel;
                        sectionLines.push(line);
                    } else if (inSection && currentLevel <= sectionLevel) {
                        // We've reached the next section at the same or higher level
                        console.log('End of section reached');
                        break;
                    } else if (inSection) {
                        sectionLines.push(line);
                    }
                } else if (inSection) {
                    sectionLines.push(line);
                }
            } else if (inSection) {
                sectionLines.push(line);
            }
        }

        const result = sectionLines.length > 0 ? sectionLines.join('\n') : null;
        if (result) {
            console.log('Section content extracted:', result.substring(0, 100) + '...');
        } else {
            console.log('Section not found');
        }
        return result;
    }

    // ... rest of the methods remain the same as in your original code
    extractBlockContent(content, blockId) {
        const lines = content.split('\n');
        let blockRefLine = null;

        // Find the line with the block reference
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.endsWith(`^${blockId}`) || line === `^${blockId}`) {
                blockRefLine = i;
                break;
            }
        }

        if (blockRefLine === null) {
            return null;
        }

        // Check if block reference is on the same line as content
        const refLine = lines[blockRefLine].trim();
        const hasContentOnSameLine = refLine !== `^${blockId}` && refLine.replace(`^${blockId}`, '').trim();

        if (hasContentOnSameLine) {
            // Block reference is inline
            const [start, end] = this.findParagraphBoundaries(lines, blockRefLine);
            if (start !== null) {
                const paragraphLines = lines.slice(start, end + 1);
                const relativeRefLine = blockRefLine - start;
                paragraphLines[relativeRefLine] = paragraphLines[relativeRefLine].replace(`^${blockId}`, '').trim();
                return paragraphLines.join('\n');
            }
            return refLine.replace(`^${blockId}`, '').trim();
        }

        // Block reference is on its own line
        let contentEnd = blockRefLine - 1;

        // Skip empty lines
        while (contentEnd >= 0 && !lines[contentEnd].trim()) {
            contentEnd--;
        }

        if (contentEnd < 0) {
            return null;
        }

        // Find content boundaries
        let contentStart, contentEndFinal;
        const lastContentLine = lines[contentEnd].trim();

        if (lastContentLine.includes('|')) {
            [contentStart, contentEndFinal] = this.findTableBoundaries(lines, contentEnd);
        } else if (this.isListItem(lastContentLine)) {
            [contentStart, contentEndFinal] = this.findListBoundaries(lines, contentEnd);
        } else if (lines[contentEnd].trim() === '```') {
            [contentStart, contentEndFinal] = this.findCodeBlockBoundaries(lines, contentEnd);
        } else {
            [contentStart, contentEndFinal] = this.findParagraphBoundaries(lines, contentEnd);
        }

        if (contentStart !== null) {
            return lines.slice(contentStart, contentEndFinal + 1).join('\n');
        }

        return null;
    }

    // Helper methods (keeping your existing implementations)
    slugify(text) {
        if (!text) return '';
        return text.trim().toLowerCase()
            .replace(/[^\w\s-]/g, '')
            .replace(/\s+/g, '-');
    }

    escapeTooltipContent(text) {
        return text.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;')
            .replace(/\n/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    getLinkHref(fileName) {
        // Get target path
        let target = (fileLinks[fileName] || fileLinks[fileName + '.md'] || '#file-not-found')
            .replace(/\\/g, '/')
            .replace(/\.md$/i, '.html');

        console.log("Target:", target);

        // Make current file path relative to outDirectory
        const article = document.querySelector("article");
        const attributeValue = article.getAttribute('data-current-file');
        let relCurParts = attributeValue.replace(/\\/g, '/').replace(' ', '-').toLowerCase().split('/').slice(0, -1)

        // Make target path relative to outDirectory
        let relTgtParts = target.split('/').filter(Boolean);
        console.log(relTgtParts)

        // Find common prefix inside outDirectory
        let i = 0;
        while (i < relCurParts.length && i < relTgtParts.length && relCurParts[i] === relTgtParts[i]) {
            i++;
        }

        // Build relative path
        const relativePath = [...Array(relCurParts.length - i).fill('..'), ...relTgtParts.slice(i)].join('/');

        console.log("Relative path:", relativePath);

        return relativePath.replace(/ /g, '-');
    }

    // Keep all your other helper methods unchanged...
    findTableBoundaries(lines, endLine) {
        let start = endLine;
        let end = endLine;

        while (start > 0) {
            const prevLine = lines[start - 1].trim();
            if (!prevLine || !prevLine.includes('|')) break;
            start--;
        }

        while (end < lines.length - 1) {
            const nextLine = lines[end + 1].trim();
            if (!nextLine || !nextLine.includes('|')) break;
            end++;
        }

        return [start, end];
    }

    findListBoundaries(lines, endLine) {
        let start = endLine;
        let end = endLine;

        while (start > 0) {
            const prevLine = lines[start - 1].trim();
            if (!prevLine || !this.isListItem(prevLine)) break;
            start--;
        }

        while (end < lines.length - 1) {
            const nextLine = lines[end + 1].trim();
            if (!nextLine || !this.isListItem(nextLine)) break;
            end++;
        }

        return [start, end];
    }

    findCodeBlockBoundaries(lines, endLine) {
        let start = endLine;

        while (start > 0) {
            if (lines[start - 1].trim().startsWith('```')) {
                start = start - 1;
                break;
            }
            start--;
        }

        return [start, endLine];
    }

    findParagraphBoundaries(lines, refLine) {
        let start = refLine;
        let end = refLine;

        while (start > 0) {
            const prevLine = lines[start - 1].trim();
            if (!prevLine || prevLine.startsWith('#') || this.isListItem(prevLine) || 
                prevLine.startsWith('```') || prevLine.includes('|') || 
                prevLine.match(/^\[.*\]:/) || prevLine.match(/^\^[a-zA-Z0-9]{6}$/)) {
                break;
            }
            start--;
        }

        while (end < lines.length - 1) {
            const nextLine = lines[end + 1].trim();
            if (!nextLine || nextLine.startsWith('#') || this.isListItem(nextLine) || 
                nextLine.startsWith('```') || nextLine.includes('|') || 
                nextLine.match(/^\[.*\]:/) || nextLine.match(/^\^[a-zA-Z0-9]{6}$/)) {
                break;
            }
            end++;
        }

        return [start, end];
    }

    isListItem(line) {
        const trimmed = line.trim();
        return trimmed.match(/^[-*+]\s/) || trimmed.match(/^\d+\.\s/) || trimmed.startsWith('- [');
    }

    fixTableSpacing(markdownText) {
        const tableRegex = /^((?:\|.*\|\n)(?:\|[-:| ]+\|\n)(?:\|.*\|\n?)*)(\^([a-zA-Z0-9]{6})[ \t]*\n)?/gm;
        return markdownText.replace(tableRegex, (match, table, tagLine) => {
            const cleaned = table.split("\n")
                .filter(line => line.trim() !== "" && !/^\|[\s|]*\|$/.test(line))
                .join("\n");
            return `\n${cleaned}\n${tagLine ?? ""}\n`;
        });
    }

    processWikilinks(content) {
        return content.replace(/\[\[([^\]]+)\]\]/g, (match, link) => {
            let [pageName, alias] = link.split('|');
            alias = alias || pageName;

            alias = alias.replace(/#/g, '&nbsp;>&nbsp;');

            let section = null;
            if (pageName.includes('#')) {
                [pageName, section] = pageName.split('#');
                section = section.toLowerCase().replace(/\s+/g, '-');
            }

            let url = this.getLinkHref(pageName);
            if (section) url += '#' + section;
            if (url === '#file-not-found') {
                return `<span class="broken-link">${match}</span>`;
            }
            return `<a href="${url}" class="wikilink">${alias}</a>`;
        });
    }

    processFootnotes(content) {
        const footnotes = {};
        let footnoteCounter = 1;

        const lines = content.split('\n');
        let inBlockquote = false;
        let processedLines = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];

            if (line.trim().startsWith('>')) {
                inBlockquote = true;
            } else if (line.trim() === '' && inBlockquote) {
                let j = i + 1;
                while (j < lines.length && lines[j].trim() === '') j++;
                if (j >= lines.length || !lines[j].trim().startsWith('>')) {
                    inBlockquote = false;
                }
            } else if (!line.trim().startsWith('>') && line.trim() !== '') {
                inBlockquote = false;
            }

            if (!inBlockquote && line.match(/^\[\^([^\]]+)\]:\s*(.*)$/)) {
                const match = line.match(/^\[\^([^\]]+)\]:\s*(.*)$/);
                const [, id, text] = match;
                footnotes[id] = text;
            } else {
                processedLines.push(line);
            }
        }

        let processedContent = processedLines.join('\n');

        const contentLines = processedContent.split('\n');
        const finalLines = [];
        inBlockquote = false;

        for (const line of contentLines) {
            if (line.trim().startsWith('>')) {
                inBlockquote = true;
                finalLines.push(line);
            } else if (line.trim() === '' && inBlockquote) {
                finalLines.push(line);
            } else if (!line.trim().startsWith('>') && line.trim() !== '') {
                inBlockquote = false;
                const processedLine = line.replace(/\[\^([^\]]+)\]/g, (match, id) => {
                    if (footnotes.hasOwnProperty(id)) {
                        const tooltipContent = this.escapeTooltipContent(footnotes[id]);
                        footnoteCounter++;
                        return `<span class="fn"><a href="#fn-${id}" class="fn-link" id="fnref-${id}"><sup>[${id}]</sup></a><span class="fn-tooltip">${tooltipContent}</span></span>`;
                    }
                    return match;
                });
                finalLines.push(processedLine);
            } else {
                finalLines.push(line);
            }
        }

        processedContent = finalLines.join('\n');

        if (Object.keys(footnotes).length > 0) {
            let footnotesHtml = '<div class="footnotes"><hr><ol>';
            for (const [id, text] of Object.entries(footnotes)) {
                footnotesHtml += `<li id="fn-${id}">${text} <a href="#fnref-${id}" class="footnote-backref">↩</a></li>`;
            }
            footnotesHtml += '</ol></div>';
            processedContent += footnotesHtml;
        }

        return processedContent;
    }

    processBlockReferences(content) {
        const lines = content.split('\n');
        const processedLines = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const blockRefMatch = line.match(/\s\^([a-zA-Z0-9]{6})\s*$/);

            if (blockRefMatch) {
                const blockId = blockRefMatch[1];
                const lineWithoutRef = line.replace(/\s\^[a-zA-Z0-9]{6}\s*$/, '');

                let contentStart, contentEnd;

                if (lineWithoutRef.trim().includes('|')) {
                    [contentStart, contentEnd] = this.findTableBoundaries(lines, i);
                } else if (this.isListItem(lineWithoutRef.trim())) {
                    [contentStart, contentEnd] = this.findListBoundaries(lines, i);
                } else if (lineWithoutRef.trim() === '```') {
                    [contentStart, contentEnd] = this.findCodeBlockBoundaries(lines, i);
                } else {
                    [contentStart, contentEnd] = this.findParagraphBoundaries(lines, i);
                }

                let alreadyProcessed = false;
                for (let j = contentStart; j < Math.min(contentEnd + 1, processedLines.length); j++) {
                    if (processedLines[j]?.includes(`id="^${blockId}"`)) {
                        alreadyProcessed = true;
                        break;
                    }
                }

                if (!alreadyProcessed && contentStart < processedLines.length) {
                    processedLines[contentStart] = `<span class="anchor" id="^${blockId}"></span>${processedLines[contentStart]}`;
                } else if (!alreadyProcessed && contentStart === processedLines.length) {
                    processedLines.push(`<span class="anchor" id="^${blockId}"></span>${lineWithoutRef}`);
                } else {
                    processedLines.push(lineWithoutRef);
                }

                if (contentStart !== i && !alreadyProcessed) {
                    processedLines.push(lineWithoutRef);
                }
            } else {
                processedLines.push(line);
            }
        }

        return processedLines.join('\n');
    }

    extractHeadersFromContent(content) {
        const headers = [];
        const lines = content.split('\n');
        
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('#')) {
                const level = trimmed.length - trimmed.replace(/^#+/, '').length;
                if (level <= 6) {
                    const headerText = trimmed.substring(level).trim();
                    const headerId = this.slugify(headerText);
                    headers.push([headerText, headerId, level]);
                }
            }
        }
        
        return headers;
    }

    buildTableOfContents(headers) {
        if (!headers || headers.length === 0) {
            return '';
        }
        
        let tocHtml = '';
        const stack = [];
        
        for (const header of headers) {
            const [headerText, headerId, level] = header;
            
            // Calculate indent level
            while (stack.length > 0 && stack[stack.length - 1] >= level) {
                stack.pop();
            }
            
            const indentClass = `indent-${stack.length}`;
            tocHtml += `<p class="${indentClass}"><a href="#${headerId}">${headerText}</a></p>`;
            
            if (stack.length === 0 || stack[stack.length - 1] !== level) {
                stack.push(level);
            }
        }
        
        return tocHtml;
    }
}

// Configure marked.js
marked.setOptions({
    breaks: true,
    gfm: true,
    tables: true,
    headerIds: true,
    headerPrefix: ''
});

function postProcessing(htmlContent) {
    htmlContent = htmlContent.replace(/<\/p>\s*<p>/g, '</p><br><p>');
    htmlContent = htmlContent.replace(/<\/table>\s*<p>/g, '</table><br><p>');
    htmlContent = htmlContent.replace(/<\/table>\s*<table>/g, '</table><br><table>');
}

function preProcessing(content) {
    // Check if content starts with frontmatter
    if (content.startsWith('---\n')) {
        const endIdx = content.indexOf('\n---\n', 4);
        if (endIdx !== -1) {
            content = content.slice(endIdx + 5); // skip the ending '---\n'
        }
    }
    return content.trim()
}

// Process and render
async function renderContent() {
    let markdownContent = ''
    const article = document.querySelector("article");
    const el = document.querySelector('.top-bar');
    let isCanvasPage = false;
    console.log(el.innerHTML)
    if (el && el.innerHTML.trim().endsWith('.canvas.html')) {
        isCanvasPage = true;
    }
    if (article) {
        const attributeValue = article.getAttribute('data-current-file');
        markdownContent = preProcessing(getFile(attributeValue));
    } else {
        markdownContent = document.getElementById('markdown-content').textContent;
    }
    const processor = new ObsidianProcessor();

    try {
        // Process canvas nodes (for canvas pages)
        if (isCanvasPage) {
            console.log('Processing canvas nodes...');
            await processor.processCanvasNodes();
            console.log('Canvas nodes processed successfully');
        }
        else {
            // Extract headers from the original markdown
            const headers = processor.extractHeadersFromContent(markdownContent);
            
            // Process the markdown
            const processedContent = await processor.processMarkdown(markdownContent);
            const htmlContent = marked.parse(processedContent);
            const spacedHtmlContent = htmlContent.replace(/<\/p>\s*<p>/g, '</p><br><p>');
            document.getElementById('rendered-content').innerHTML = spacedHtmlContent;
            
            // Build and populate table of contents
            if (headers.length > 0) {
                const tocHtml = processor.buildTableOfContents(headers);
                document.getElementById('toc-content').innerHTML = tocHtml;
                document.getElementById('table-of-contents').style.removeProperty('display');
            }
        }
    } catch (error) {
        console.error('Error processing markdown:', error);
        document.getElementById('rendered-content').innerHTML = '<p>Error processing content. Please check the console for details.</p>';
    }
}

// Render when page loads
document.addEventListener('DOMContentLoaded', renderContent);

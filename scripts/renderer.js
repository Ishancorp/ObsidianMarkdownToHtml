// Note: This file CANNOT be run in this state. It must be processed first, plopping in relevant content in these four consts here. 

const fileLinks = {/*file_links*/}
const fileContentMap = {/*file_content_map*/}
const fileContents = {/*file_contents*/}
const fileProperties = {/*file_properties*/}
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

class CanvasProcessor {
    constructor() {
        this.CANVAS_OFFSET_X = 750;
        this.CANVAS_OFFSET_Y = 400;
        this.MIN_NODE_WIDTH = 50;
        this.MIN_NODE_HEIGHT = 30;
        this.DEFAULT_NODE_WIDTH = 200;
        this.DEFAULT_NODE_HEIGHT = 100;
        this.MIN_CANVAS_WIDTH = 1500;
        this.MIN_CANVAS_HEIGHT = 1000;
        this.CANVAS_PADDING = 1000;
        this.VALID_SIDES = new Set(["left", "right", "top", "bottom"]);
    }

    async processCanvas(jsonContent) {
        try {
            const data = JSON.parse(jsonContent);
            const nodes = data.nodes || [];
            const edges = data.edges || [];
            
            const { nodesById, divPart, maxX, maxY } = await this.processNodes(nodes);
            const { svgPart, arrowPart } = this.processEdges(edges, nodesById, maxX, maxY);
            
            return this.buildFinalHTML(divPart, svgPart, arrowPart);
        } catch (error) {
            return `<div class="error">Error processing canvas: ${this.escapeHtml(error.message)}</div>`;
        }
    }

    async processNodes(nodes) {
        const nodesById = {};
        let divPart = "";
        let maxX = 0;
        let maxY = 0;
        const processor = new ObsidianProcessor();

        for (const node of nodes) {
            if (!node.id) continue;
            
            const x = parseFloat(node.x || 0);
            const y = parseFloat(node.y || 0);
            const width = Math.max(parseFloat(node.width || this.DEFAULT_NODE_WIDTH), this.MIN_NODE_WIDTH);
            const height = Math.max(parseFloat(node.height || this.DEFAULT_NODE_HEIGHT), this.MIN_NODE_HEIGHT);
            const text = node.text || "";
            const color = node.color || "";
            
            const divClasses = this.generateNodeClasses(color);
            const leftPos = x + this.CANVAS_OFFSET_X;
            const topPos = y + this.CANVAS_OFFSET_Y;
            
            // Process markdown content
            let processedContent = "";
            if (text) {
                try {
                    const processedMarkdown = await processor.processMarkdown(text);
                    processedContent = marked.parse(processedMarkdown);
                } catch (error) {
                    processedContent = this.escapeHtml(text);
                }
            }
            
            divPart += `<div class="${divClasses.join(' ')}" id="${this.escapeHtml(node.id)}" style="left:${leftPos}px;top:${topPos}px;width:${width}px;height:${height}px">\n${processedContent}\n</div>\n`;
            
            nodesById[node.id] = {
                left: [x, y + height/2],
                right: [x + width, y + height/2],
                top: [x + width/2, y],
                bottom: [x + width/2, y + height]
            };
            
            maxX = Math.max(maxX, x + width);
            maxY = Math.max(maxY, y + height);
        }
        
        return { nodesById, divPart, maxX, maxY };
    }

    processEdges(edges, nodesById, maxX, maxY) {
        const svgWidth = Math.max(maxX + this.CANVAS_PADDING, this.MIN_CANVAS_WIDTH);
        const svgHeight = Math.max(maxY + this.CANVAS_PADDING, this.MIN_CANVAS_HEIGHT);
        
        let svgPart = `<svg id="svg" width="${svgWidth}" height="${svgHeight}">\n`;
        let arrowPart = "";
        
        for (const edge of edges) {
            if (!edge.fromNode || !edge.toNode || !nodesById[edge.fromNode] || !nodesById[edge.toNode]) {
                continue;
            }
            
            const fromSide = this.VALID_SIDES.has(edge.fromSide) ? edge.fromSide : "right";
            const toSide = this.VALID_SIDES.has(edge.toSide) ? edge.toSide : "left";
            
            const nodeFrom = nodesById[edge.fromNode];
            const nodeTo = nodesById[edge.toNode];
            
            const x1 = nodeFrom[fromSide][0] + this.CANVAS_OFFSET_X;
            const y1 = nodeFrom[fromSide][1] + this.CANVAS_OFFSET_Y;
            const x2 = nodeTo[toSide][0] + this.CANVAS_OFFSET_X;
            const y2 = nodeTo[toSide][1] + this.CANVAS_OFFSET_Y;
            
            svgPart += `<line class="line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>\n`;
            arrowPart += this.generateArrowHTML(toSide, x2, y2);
        }
        
        svgPart += "</svg>\n";
        return { svgPart, arrowPart };
    }

    generateNodeClasses(color) {
        const classes = ["general-boxes"];
        if (color && typeof color === 'string') {
            const sanitized = color.replace(/[^a-zA-Z0-9\-_]/g, '');
            if (sanitized) classes.push(`color-${sanitized}`);
        }
        return classes;
    }

    generateArrowHTML(toSide, arrowX, arrowY) {
        if (toSide === "left") {
            return `<i class="arrow ${toSide}" style="left:${arrowX - 10}px;top:${arrowY - 5}px;"></i>\n`;
        }
        return `<i class="arrow ${toSide}" style="left:${arrowX - 5}px;top:${arrowY - 10}px;"></i>\n`;
    }

    buildFinalHTML(divPart, svgPart, arrowPart) {
        return `<div id="outer-box">
<div id="scrollable-box">
<div id="innard">${arrowPart}${svgPart}${divPart}</div>
</div>
</div>`;
    }

    escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }
}

class BaseProcessor extends ObsidianProcessor {
    async processBase(yamlContent) {
        try {
            const data = JSON.parse(yamlContent);
            console.log('Parsed base data:', data);
            
            if (!data.views || !data.views[0]) {
                return '<div class="error">Invalid base file: No views defined</div>';
            }
            
            const viewType = data.views[0].type;
            console.log('Processing view type:', viewType);
            
            if (viewType === "table") {
                return await this.processTable(data); // Add await
            } else if (viewType === "cards") {
                return await this.processCards(data); // Add await
            }
            
            return '<div class="error">Unsupported view type</div>';
        } catch (error) {
            console.error('Base processing error:', error);
            return `<div class="error">Error processing base: ${this.escapeHtml(error.message)}</div>`;
        }
    }

    async processTable(data) {
        const props = this.getProps(data);
        const filteredLinks = this.getFilteredLinks(data);
        
        console.log('Props:', props);
        console.log('Filtered links:', filteredLinks);
        
        if (filteredLinks.length === 0) {
            return '<div class="info">No files match the specified filters</div>';
        }
        
        let propOrder = Object.keys(props);
        if (data.views && data.views[0] && data.views[0].order) {
            propOrder = data.views[0].order;
        }
        
        let tableHtml = '<table>\n<thead>\n<tr>\n';
        
        for (const key of propOrder) {
            if (props[key]) {
                tableHtml += `<th>${this.escapeHtml(props[key])}</th>\n`;
            }
        }
        tableHtml += '</tr>\n</thead>\n<tbody>\n';
        
        for (const link of filteredLinks) {
            tableHtml += '<tr>\n';
            for (const key of propOrder) {
                if (props[key]) {
                    const value = await this.getPropertyValue(link, key); // Add await
                    tableHtml += `<td>${value}</td>\n`;
                }
            }
            tableHtml += '</tr>\n';
        }
        
        tableHtml += '</tbody>\n</table>\n';
        return tableHtml;
    }

    async processCards(data) {
        const props = this.getProps(data);
        const filteredLinks = this.getFilteredLinks(data);
        const viewConfig = data.views[0];
        
        console.log('Cards - Props:', props);
        console.log('Cards - Filtered links:', filteredLinks);
        
        if (filteredLinks.length === 0) {
            return '<div class="info">No files match the specified filters</div>';
        }
        
        let cardsHtml = '<div class="cards-container">\n';
        
        for (const link of filteredLinks) {
            const fileLink = this.getFileLinkHref(link);
            
            cardsHtml += `<div class="card" data-href="${fileLink}">\n`;
            cardsHtml += '<div class="card-content">\n';
            
            // Handle image if specified
            if (viewConfig.image) {
                const imageValue = await this.getPropertyValue(link, viewConfig.image); // Add await
                if (imageValue && !imageValue.includes('<a href')) {
                    const imageFit = viewConfig.imageFit || 'cover';
                    cardsHtml += `<div class="card-image">\n`;
                    cardsHtml += `<img src="${imageValue}" alt="${this.escapeHtml(link)}" style="object-fit: ${imageFit};" />\n`;
                    cardsHtml += `</div>\n`;
                }
                else {
                    cardsHtml += `<div class="card-image">\n</div>`
                }
            }
            
            cardsHtml += `<h3 class="card-title"><a href="${fileLink}">${this.escapeHtml(link)}</a></h3>\n`;
            
            for (const propKey in props) {
                if (propKey !== 'file.name' && propKey !== viewConfig.image) {
                    const propValue = await this.getPropertyValue(link, propKey); // Add await
                    if (propValue) {
                        cardsHtml += `<div class="card-property">\n`;
                        cardsHtml += `<span class="property-label">${this.escapeHtml(props[propKey])}:</span>\n`;
                        cardsHtml += `<span class="property-value">${propValue}</span>\n`;
                        cardsHtml += `</div>\n`;
                    }
                }
            }
            
            cardsHtml += '</div>\n</div>\n';
        }
        
        cardsHtml += '</div>\n';
        return cardsHtml;
    }

    getFilteredLinks(data) {
        // Get ALL files, not just ones in fileLinks
        const allFileIds = Object.keys(fileProperties);
        console.log('All file IDs:', allFileIds.length);
        
        // Convert to file names/links with deduplication
        const allLinks = [];
        const seenLinks = new Set(); // Track duplicates
        
        for (const fileId of allFileIds) {
            const fileProps = fileProperties[fileId];
            if (fileProps && fileProps.path) {
                // Use the filename without extension as the link
                const filename = fileProps.file ? fileProps.file.replace(/\.[^/.]+$/, "") : fileProps.path.split('/').pop().replace(/\.[^/.]+$/, "");
                
                // Only add if we haven't seen this link before
                if (!seenLinks.has(filename)) {
                    seenLinks.add(filename);
                    allLinks.push(filename);
                }
            }
        }
        
        console.log('All links before filtering (deduplicated):', allLinks);
        
        // Apply filters
        let filteredLinks = allLinks;
        if (data.views && data.views[0] && data.views[0].filters) {
            const filters = data.views[0].filters;
            
            filteredLinks = allLinks.filter(link => {
                let include = true;
                
                if (filters.and) {
                    for (const filter of filters.and) {
                        const result = this.evaluateFilter(filter, link);
                        console.log(`Filter "${filter}" on "${link}":`, result);
                        include = include && result;
                    }
                }
                
                return include;
            });
        }
        
        console.log('Filtered links:', filteredLinks);
        
        // Sort the results
        return this.sortLinks(data, filteredLinks);
    }

    getProps(data) {
        const props = {};
        if (data.properties) {
            for (const key in data.properties) {
                props[key] = data.properties[key].displayName || key;
            }
        } else {
            // If no properties defined, create default ones based on filters/order
            if (data.views && data.views[0]) {
                const view = data.views[0];
                if (view.order) {
                    for (const prop of view.order) {
                        props[prop] = this.formatPropertyName(prop);
                    }
                }
            }
        }
        return props;
    }

    formatPropertyName(propKey) {
        // Convert property keys to display names
        if (propKey === 'file.name') return 'Name';
        if (propKey === 'file.folder') return 'Folder';
        if (propKey === 'file.path') return 'Path';
        if (propKey === 'file.ext') return 'Extension';
        if (propKey === 'file.basename') return 'Basename';
        
        // For note properties, just use the key
        return propKey.replace('note.', '').replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
    }

    async getPropertyValue(link, propKey) {
        const fileId = this.findFileIdByLink(link);
        if (!fileId) {
            console.log(`No file ID found for link: ${link}`);
            return '';
        }
        
        const fileProps = fileProperties[fileId];
        if (!fileProps) {
            console.log(`No file properties found for ID: ${fileId}`);
            return '';
        }
        
        if (propKey === 'file.name') {
            const targetLink = this.getFileLinkHref(link);
            return `<a href="${targetLink}">${this.escapeHtml(link)}</a>`;
        }
        
        if (propKey.startsWith('file.')) {
            const fileProp = propKey.substring(5);
            const value = fileProps[fileProp];
            return this.escapeHtml(value || '');
        }
        
        if (propKey.startsWith('note.')) {
            console.log(21414)
            console.log(propKey)
            if (!fileProps.notes) return '';
            
            const noteProp = propKey.substring(5);
            let noteValue = fileProps.notes[noteProp];
            console.log(noteValue)
            
            if (!noteValue) return '';
            
            // Check if this is a wikilink (like an image reference)
            if (typeof noteValue === 'string' && noteValue.startsWith('"[[') && noteValue.endsWith(']]"')) {
                const linkContent = noteValue.slice(3, -3); // Remove "[[ ]]"
                
                // Check if it's an image
                if (linkContent.includes('.')) {
                    const extension = linkContent.split('.').pop().toLowerCase();
                    if (this.image_types.has(extension)) {
                        // Return the image URL directly for image properties
                        const imageUrl = this.getLinkHref(linkContent);
                        console.log(imageUrl)
                        console.log(69)
                        if (imageUrl !== '#file-not-found') {
                            return imageUrl;
                        }
                        return '';
                    }
                }
                
                // For non-image wikilinks, convert to regular link
                const targetUrl = this.getLinkHref(linkContent);
                if (targetUrl !== '#file-not-found') {
                    return targetUrl;
                }
                return '';
            }
            
            // Process other note values through ObsidianProcessor pipeline
            const processedContent = await this.processMarkdown(noteValue, link);
            return processedContent;
        }
        
        // Handle direct property access from notes
        if (!fileProps.notes) return '';
        
        let noteValue = fileProps.notes[propKey];
        if (!noteValue) return '';
        
        // Check if this is a wikilink (like an image reference)
        if (typeof noteValue === 'string' && noteValue.startsWith('[[') && noteValue.endsWith(']]')) {
            const linkContent = noteValue.slice(2, -2); // Remove [[ ]]
            
            // Check if it's an image
            if (linkContent.includes('.')) {
                const extension = linkContent.split('.').pop().toLowerCase();
                if (this.image_types.has(extension)) {
                    // Return the image URL directly for image properties
                    const imageUrl = this.getLinkHref(linkContent);
                    if (imageUrl !== '#file-not-found') {
                        return imageUrl;
                    }
                    return '';
                }
            }
            
            // For non-image wikilinks, convert to regular link
            const targetUrl = this.getLinkHref(linkContent);
            if (targetUrl !== '#file-not-found') {
                return targetUrl;
            }
            return '';
        }
        
        // Process through ObsidianProcessor pipeline
        const processedContent = await this.processMarkdown(noteValue, link);
        return processedContent;
    }

    findFileIdByLink(link) {
        // Try direct lookup first
        if (fileContentMap[link]) {
            return fileContentMap[link];
        }
        
        // Search through all file properties
        for (const [fileId, props] of Object.entries(fileProperties)) {
            if (props.file) {
                const basename = props.file.replace(/\.[^/.]+$/, "");
                if (basename === link) {
                    return fileId;
                }
            }
        }
        
        return null;
    }

    getFileLinkHref(filename) {
        // Use the same logic as getLinkHref() from ObsidianProcessor
        let target = (fileLinks[filename] || fileLinks[filename + '.md'] || '#file-not-found')
            .replace(/\\/g, '/')
            .replace(/\.md$/i, '.html');

        if (target === '#file-not-found') {
            return '#';
        }

        // Make current file path relative to outDirectory
        const article = document.querySelector("article");
        const attributeValue = article.getAttribute('data-current-file');
        let relCurParts = attributeValue.replace(/\\/g, '/').replace(' ', '-').toLowerCase().split('/').slice(0, -1);

        // Make target path relative to outDirectory
        let relTgtParts = target.split('/').filter(Boolean);

        // Find common prefix inside outDirectory
        let i = 0;
        while (i < relCurParts.length && i < relTgtParts.length && relCurParts[i] === relTgtParts[i]) {
            i++;
        }

        // Build relative path
        const relativePath = [...Array(relCurParts.length - i).fill('..'), ...relTgtParts.slice(i)].join('/');

        return relativePath.replace(/ /g, '-');
    }

    evaluateFilter(filter, link) {
        const fileId = this.findFileIdByLink(link);
        if (!fileId) {
            console.log(`No file ID for link ${link} in filter evaluation`);
            return false;
        }
        
        const fileProps = fileProperties[fileId];
        if (!fileProps) {
            console.log(`No file properties for ID ${fileId} in filter evaluation`);
            return false;
        }
        
        console.log(`Evaluating filter "${filter}" for file:`, fileProps);
        
        // Handle startsWith filters
        if (filter.includes('.startsWith(')) {
            const match = filter.match(/^(.+)\.startsWith\(["'](.+)["']\)$/);
            if (match) {
                const [, property, value] = match;
                
                if (property === 'file.folder') {
                    const result = fileProps.folder && fileProps.folder.startsWith(value);
                    console.log(`  file.folder "${fileProps.folder}" startsWith "${value}":`, result);
                    return result;
                } else if (property === 'file.path') {
                    const result = fileProps.path && fileProps.path.startsWith(value);
                    console.log(`  file.path "${fileProps.path}" startsWith "${value}":`, result);
                    return result;
                }
            }
            return false;
        }
        
        // Handle equality filters
        if (filter.includes(' == ')) {
            const [pre, post] = filter.split(' == ');
            const expectedValue = post.replace(/^["']|["']$/g, ''); // Remove quotes
            
            if (pre.startsWith('file.')) {
                const prop = pre.substring(5);
                const actualValue = fileProps[prop];
                const result = actualValue === expectedValue;
                console.log(`  ${pre} "${actualValue}" == "${expectedValue}":`, result);
                return result;
            } else {
                // Check in notes
                if (!fileProps.notes) {
                    console.log(`  No notes for property "${pre}"`);
                    return false;
                }
                const actualValue = fileProps.notes[pre];
                const result = actualValue === expectedValue;
                console.log(`  note.${pre} "${actualValue}" == "${expectedValue}":`, result);
                return result;
            }
        }
        
        // Handle inequality filters  
        if (filter.includes(' != ')) {
            const [pre, post] = filter.split(' != ');
            const expectedValue = post.replace(/^["']|["']$/g, '');
            
            if (pre.startsWith('file.')) {
                const prop = pre.substring(5);
                const actualValue = fileProps[prop];
                const result = actualValue !== expectedValue;
                console.log(`  ${pre} "${actualValue}" != "${expectedValue}":`, result);
                return result;
            } else {
                if (!fileProps.notes || !fileProps.notes[pre]) {
                    console.log(`  No notes for property "${pre}" - treating as != "${expectedValue}": true`);
                    return true; // If no notes, then property doesn't exist, so != is true
                }
                const actualValue = fileProps.notes[pre].slice(1, -1);
                const result = !actualValue || actualValue !== expectedValue;
                console.log(`  note.${pre} "${actualValue}" != "${expectedValue}":`, result);
                return result;
            }
        }
        
        console.log(`  Unknown filter format: "${filter}"`);
        return true;
    }

    // Fixed sorting method for BaseProcessor class

    sortLinks(data, links) {
        if (!data.views || !data.views[0] || !data.views[0].sort) {
            return links;
        }
        
        const sortRules = data.views[0].sort; // Remove the reverse - process in original order
        
        return links.sort((a, b) => {
            // Process sort rules in order (most important first)
            for (const rule of sortRules) {
                const prop = rule.property;
                const isAscending = rule.direction === 'ASC';
                
                let aVal = this.getSortValue(a, prop);
                let bVal = this.getSortValue(b, prop);
                
                // Handle null/undefined values - sort them to the end
                if ((aVal === null || aVal === undefined || aVal === '') && 
                    (bVal === null || bVal === undefined || bVal === '')) {
                    continue; // Both empty, check next sort rule
                }
                if (aVal === null || aVal === undefined || aVal === '') {
                    return isAscending ? 1 : -1; // Empty values go to end for ASC, beginning for DESC
                }
                if (bVal === null || bVal === undefined || bVal === '') {
                    return isAscending ? -1 : 1;
                }
                
                // Determine if values are numeric
                const aNum = parseFloat(aVal);
                const bNum = parseFloat(bVal);
                const aIsNum = !isNaN(aNum) && isFinite(aNum);
                const bIsNum = !isNaN(bNum) && isFinite(bNum);
                
                let comparison = 0;
                
                if (aIsNum && bIsNum) {
                    // Numeric comparison
                    comparison = aNum - bNum;
                } else {
                    // String comparison (case-insensitive)
                    const aStr = String(aVal).toLowerCase();
                    const bStr = String(bVal).toLowerCase();
                    comparison = aStr.localeCompare(bStr);
                }
                
                if (comparison !== 0) {
                    return isAscending ? comparison : -comparison;
                }
            }
            
            // If all sort rules result in equality, maintain original order
            return 0;
        });
    }

    getSortValue(link, property) {
        const fileId = this.findFileIdByLink(link);
        if (!fileId) return '';
        
        const fileProps = fileProperties[fileId];
        if (!fileProps) return '';
        
        // Handle file properties
        if (property.startsWith('file.')) {
            const fileProp = property.substring(5);
            
            if (fileProp === 'basename' || fileProp === 'name') {
                return fileProps.file ? fileProps.file.replace(/\.[^/.]+$/, "") : '';
            } else if (fileProp === 'folder') {
                return fileProps.folder || '';
            } else if (fileProp === 'path') {
                return fileProps.path || '';
            } else if (fileProp === 'ext') {
                return fileProps.ext || '';
            } else {
                return fileProps[fileProp] || '';
            }
        }
        
        // Handle note properties
        if (property.startsWith('note.')) {
            const noteProp = property.substring(5);
            if (!fileProps.notes) return '';
            const noteValue = fileProps.notes[noteProp];
            
            // Clean up quoted values
            if (typeof noteValue === 'string' && noteValue.startsWith('"') && noteValue.endsWith('"')) {
                return noteValue.slice(1, -1);
            }
            
            return noteValue || '';
        }
        
        // Handle direct property access from notes
        if (!fileProps.notes) return '';
        const noteValue = fileProps.notes[property];
        
        // Clean up quoted values
        if (typeof noteValue === 'string' && noteValue.startsWith('"') && noteValue.endsWith('"')) {
            return noteValue.slice(1, -1);
        }
        
        return noteValue || '';
    }

    escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
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

// Process and render
async function renderContent() {
    const article = document.querySelector("article");
    const el = document.querySelector('.top-bar');
    
    let fileType = "md";
    if (el && el.innerHTML.trim().endsWith('.canvas.html')) {
        fileType = "canvas";
    } else if (el && el.innerHTML.trim().endsWith('.base.html')) {
        fileType = "base";
    }

    const processor = new ObsidianProcessor();
    const canvasProcessor = new CanvasProcessor();
    const baseProcessor = new BaseProcessor();

    try {
        article.classList.add(fileType)
        const attributeValue = article.getAttribute('data-current-file');
        const content = getFile(attributeValue);
        let processedHTML = ''
        if (fileType === "canvas") {
            processedHTML = await canvasProcessor.processCanvas(content);
        } else if (fileType === "base") {
            processedHTML = await baseProcessor.processBase(content); // Already awaited, good
        } else {
            // Regular markdown processing
            const headers = processor.extractHeadersFromContent(content);
            const processedContent = await processor.processMarkdown(content);
            const htmlContent = marked.parse(processedContent);
            processedHTML = htmlContent.replace(/<\/p>\s*<p>/g, '</p><br><p>');
            
            if (headers.length > 0) {
                const tocHtml = processor.buildTableOfContents(headers);
                document.getElementById('toc-content').innerHTML = tocHtml;
                document.getElementById('table-of-contents').style.removeProperty('display');
            }
        }
        article.innerHTML = processedHTML
    } catch (error) {
        console.error('Error processing content:', error);
        article.innerHTML = '<p>Error processing content. Please check the console for details.</p>';
    }
}

// Render when page loads
document.addEventListener('DOMContentLoaded', renderContent);

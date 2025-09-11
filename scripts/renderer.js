// Note: This file CANNOT be run in this state. It must be processed first, plopping in relevant content in these four consts here. 

const fileLinks = {/*file_links*/}
const fileContentMap = {/*file_content_map*/}
const fileContents = {/*file_contents*/}
const fileProperties = {/*file_properties*/}
const inDirectory = /*in_directory*/0
const outDirectory = /*out_directory*/0

function getFile(id){
    return fileContents[fileContentMap[id]];
}

class ObsidianProcessor {
    constructor() {
        this.image_types = new Set(['png', 'svg', 'jpg', 'jpeg', 'gif', 'webp']);
        this.transclusion_depth = 0;
        this.max_transclusion_depth = 5;
        this.processing_files = new Set();
        this.canvas_constants = {
            CANVAS_OFFSET_X: 750,
            CANVAS_OFFSET_Y: 400,
            MIN_NODE_WIDTH: 50,
            MIN_NODE_HEIGHT: 30,
            DEFAULT_NODE_WIDTH: 200,
            DEFAULT_NODE_HEIGHT: 100,
            MIN_CANVAS_WIDTH: 1500,
            MIN_CANVAS_HEIGHT: 1000,
            CANVAS_PADDING: 1000,
            VALID_SIDES: new Set(["left", "right", "top", "bottom"]),
        }
    }

    async processMarkdown(content, currentFile = null) {
        content = this.preprocessHeaders(content);
        
        content = this.fixTableSpacing(content);
        
        content = await this.processTransclusions(content, currentFile);
        
        content = this.processWikilinks(content);
        
        content = this.processFootnotes(content);
        
        content = this.processBlockReferences(content);
        
        return content;
    }

    async processCanvas(jsonContent) {
        try {
            const data = JSON.parse(jsonContent);
            const nodes = data.nodes || [];
            const edges = data.edges || [];

            //process nodes
            const nodesById = {};
            let divPart = "";
            let maxX = 0;
            let maxY = 0;

            for (const node of nodes) {
                if (!node.id) continue;
                
                const x = parseFloat(node.x || 0);
                const y = parseFloat(node.y || 0);
                const width = Math.max(parseFloat(node.width || this.canvas_constants.DEFAULT_NODE_WIDTH), this.canvas_constants.MIN_NODE_WIDTH);
                const height = Math.max(parseFloat(node.height || this.canvas_constants.DEFAULT_NODE_HEIGHT), this.canvas_constants.MIN_NODE_HEIGHT);
                const text = node.text || "";
                const color = node.color || "";
                
                const divClasses = ["general-boxes"];
                if (color && typeof color === 'string') {
                    const sanitized = color.replace(/[^a-zA-Z0-9\-_]/g, '');
                    if (sanitized) divClasses.push(`color-${sanitized}`);
                }
                const leftPos = x + this.canvas_constants.CANVAS_OFFSET_X;
                const topPos = y + this.canvas_constants.CANVAS_OFFSET_Y;
                
                let processedContent = "";
                if (text) {
                    try {
                        const processedMarkdown = await this.processMarkdown(text);
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
            

            //process edges
            const svgWidth = Math.max(maxX + this.canvas_constants.CANVAS_PADDING, this.canvas_constants.MIN_CANVAS_WIDTH);
            const svgHeight = Math.max(maxY + this.canvas_constants.CANVAS_PADDING, this.canvas_constants.MIN_CANVAS_HEIGHT);
            
            let svgPart = `<svg id="svg" width="${svgWidth}" height="${svgHeight}">\n`;
            let arrowPart = "";
            
            for (const edge of edges) {
                if (!edge.fromNode || !edge.toNode || !nodesById[edge.fromNode] || !nodesById[edge.toNode]) {
                    continue;
                }
                
                const fromSide = this.canvas_constants.VALID_SIDES.has(edge.fromSide) ? edge.fromSide : "right";
                const toSide = this.canvas_constants.VALID_SIDES.has(edge.toSide) ? edge.toSide : "left";
                
                const nodeFrom = nodesById[edge.fromNode];
                const nodeTo = nodesById[edge.toNode];
                
                const x1 = nodeFrom[fromSide][0] + this.canvas_constants.CANVAS_OFFSET_X;
                const y1 = nodeFrom[fromSide][1] + this.canvas_constants.CANVAS_OFFSET_Y;
                const x2 = nodeTo[toSide][0] + this.canvas_constants.CANVAS_OFFSET_X;
                const y2 = nodeTo[toSide][1] + this.canvas_constants.CANVAS_OFFSET_Y;
                
                svgPart += `<line class="line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>\n`;
                if (toSide === "left") {
                    arrowPart += `<i class="arrow ${toSide}" style="left:${x2 - 10}px;top:${y2 - 5}px;"></i>\n`;
                }
                else {
                    arrowPart += `<i class="arrow ${toSide}" style="left:${x2 - 5}px;top:${y2 - 10}px;"></i>\n`;
                }
            }
            svgPart += "</svg>\n";
            
            return `<div id="outer-box">
<div id="scrollable-box">
<div id="innard">${arrowPart}${svgPart}${divPart}</div>
</div>
</div>`;
        } catch (error) {
            return `<div class="error">Error processing canvas: ${this.escapeHtml(error.message)}</div>`;
        }
    }

    async processBase(yamlContent) {
        try {
            const data = JSON.parse(yamlContent);
            console.log('Parsed base data:', data);
            
            if (!data.views || !data.views[0]) {
                return '<div class="error">Invalid base file: No views defined</div>';
            }
            
            const viewType = data.views[0].type;
            console.log('Processing view type:', viewType);
            
            const props = {};
            if (data.properties) {
                for (const key in data.properties) {
                    props[key] = data.properties[key].displayName || key;
                }
            } else {
                if (data.views && data.views[0]) {
                    const view = data.views[0];
                    if (view.order) {
                        for (const prop of view.order) {
                            if (prop === 'file.name') props[prop] = 'Name';
                            if (prop === 'file.folder') props[prop] = 'Folder';
                            if (prop === 'file.path') props[prop] = 'Path';
                            if (prop === 'file.ext') props[prop] = 'Extension';
                            if (prop === 'file.basename') props[prop] = 'Basename';
                            else props[prop] = prop.replace('note.', '').replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
                        }
                    }
                }
            }
            const allFileIds = Object.keys(fileProperties);
            console.log('All file IDs:', allFileIds.length);
            
            const allLinks = [];
            const seenLinks = new Set();
            
            for (const fileId of allFileIds) {
                const fileProps = fileProperties[fileId];
                if (fileProps && fileProps.path) {
                    let filename;
                    if (fileProps.file && fileProps.ext && 
                        !['md', 'canvas', 'base'].includes(fileProps.ext.toLowerCase())) {
                        filename = fileProps.file;
                    } else {
                        filename = fileProps.file ? fileProps.file.replace(/\.[^/.]+$/, "") : fileProps.path.split('/').pop().replace(/\.[^/.]+$/, "");
                    }
                    
                    if (!seenLinks.has(filename)) {
                        seenLinks.add(filename);
                        allLinks.push(filename);
                    }
                }
            }
            
            console.log('All links before filtering (deduplicated):', allLinks);
            
            let filteredLinks = allLinks;
            if (data.views && data.views[0] && data.views[0].filters) {
                const filters = data.views[0].filters;
                
                filteredLinks = allLinks.filter(link => {
                    let include = true;
                    
                    if (filters.and) {
                        for (const filter of filters.and) {
                            const fileId = this.findFileIdByLink(link);
                            const result = (function () {
                                const fileProps = fileId ? fileProperties[fileId] : "";
                                if (!fileId) {
                                    console.log(`No file ID for link ${link} in filter evaluation`);
                                    return false;
                                } else if (!fileProps) {
                                    console.log(`No file properties for ID ${fileId} in filter evaluation`);
                                    return false;
                                } else if (filter.includes('.startsWith(')) {
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
                                    } else {
                                        return false;
                                    }
                                } else if (filter.includes(' == ')) {
                                    const [pre, post] = filter.split(' == ');
                                    const expectedValue = post.replace(/^["']|["']$/g, '');
                                    
                                    if (pre.startsWith('file.')) {
                                        const prop = pre.substring(5);
                                        const actualValue = fileProps[prop];
                                        const result = actualValue === expectedValue;
                                        console.log(`  ${pre} "${actualValue}" == "${expectedValue}":`, result);
                                        return result;
                                    } else {
                                        if (!fileProps.notes) {
                                            console.log(`  No notes for property "${pre}"`);
                                            return false;
                                        }
                                        const actualValue = fileProps.notes[pre];
                                        const result = actualValue === expectedValue;
                                        console.log(`  note.${pre} "${actualValue}" == "${expectedValue}":`, result);
                                        return result;
                                    }
                                } else if (filter.includes(' != ')) {
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
                                            return true;
                                        }
                                        const actualValue = fileProps.notes[pre].slice(1, -1);
                                        const result = !actualValue || actualValue !== expectedValue;
                                        console.log(`  note.${pre} "${actualValue}" != "${expectedValue}":`, result);
                                        return result;
                                    }
                                } else {
                                    console.log(`  Unknown filter format: "${filter}"`);
                                    return true;
                                }
                            })()
                            console.log(`Filter "${filter}" on "${link}":`, result);
                            include = include && result;
                        }
                    }
                    return include;
                });
            }
            
            console.log('Filtered links:', filteredLinks);
            
            const sortRules = data.views[0].sort || [];
            
            const sortedLinks = filteredLinks.sort((a, b) => {
                for (const rule of sortRules) {
                    const prop = rule.property;
                    const isAscending = rule.direction === 'ASC';
                    
                    let aVal = this.getSortValue(a, prop);
                    let bVal = this.getSortValue(b, prop);
                    
                    if ((aVal === null || aVal === undefined || aVal === '') && 
                        (bVal === null || bVal === undefined || bVal === '')) {
                        continue;
                    }
                    if (aVal === null || aVal === undefined || aVal === '') {
                        return isAscending ? 1 : -1;
                    }
                    if (bVal === null || bVal === undefined || bVal === '') {
                        return isAscending ? -1 : 1;
                    }
                    
                    const aNum = parseFloat(aVal);
                    const bNum = parseFloat(bVal);
                    const aIsNum = !isNaN(aNum) && isFinite(aNum);
                    const bIsNum = !isNaN(bNum) && isFinite(bNum);
                    
                    let comparison = 0;
                    
                    if (aIsNum && bIsNum) {
                        comparison = aNum - bNum;
                    } else {
                        const aStr = String(aVal).toLowerCase();
                        const bStr = String(bVal).toLowerCase();
                        comparison = aStr.localeCompare(bStr);
                    }
                    
                    if (comparison !== 0) {
                        return isAscending ? comparison : -comparison;
                    }
                }
                
                return 0;
            });

            const viewConfig = data.views ? data.views[0] : {};
            
            console.log('Props:', props);
            console.log('Sorted links:', sortedLinks);
            
            if (viewType === "table") {
                if (sortedLinks.length === 0) {
                    return '<div class="info">No files match the specified filters</div>';
                }
                
                let propOrder = Object.keys(props);
                if (data.views && viewConfig && viewConfig.order) {
                    propOrder = viewConfig.order;
                }
                
                let tableHtml = '<table>\n<thead>\n<tr>\n';
                
                for (const key of propOrder) {
                    if (props[key]) {
                        tableHtml += `<th>${this.escapeHtml(props[key])}</th>\n`;
                    }
                }
                tableHtml += '</tr>\n</thead>\n<tbody>\n';
                
                for (const link of sortedLinks) {
                    tableHtml += '<tr>\n';
                    for (const key of propOrder) {
                        if (props[key]) {
                            const value = await this.getPropertyValue(link, key);
                            tableHtml += `<td>${value}</td>\n`;
                        }
                    }
                    tableHtml += '</tr>\n';
                }
                
                tableHtml += '</tbody>\n</table>\n';
                return tableHtml;
            } else if (viewType === "cards") {
                
                if (sortedLinks.length === 0) {
                    return '<div class="info">No files match the specified filters</div>';
                }
                
                let cardsHtml = '<div class="cards-container">\n';
                
                for (const link of sortedLinks) {
                    const fileLink = this.getLinkHref(link);
                    
                    cardsHtml += `<div class="card" data-href="${fileLink}">\n`;
                    cardsHtml += '<div class="card-content">\n';
                    
                    if (viewConfig.image) {
                        const imageValue = await this.getPropertyValue(link, viewConfig.image);
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
                            const propValue = await this.getPropertyValue(link, propKey);
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
            
            return '<div class="error">Unsupported view type</div>';
        } catch (error) {
            console.error('Base processing error:', error);
            return `<div class="error">Error processing base: ${this.escapeHtml(error.message)}</div>`;
        }
    }

    async processFile(content, fileType) {
        if (fileType == "base") {
            return [await this.processBase(content), []]
        } if (fileType == "canvas") {
            return [await this.processCanvas(content), []];
        }
        else {
            const headers = this.extractHeadersFromContent(content);
            const processedContent = await this.processMarkdown(content);
            
            console.log('Processed content before marked:', processedContent.substring(0, 500));
            
            const htmlContent = marked.parse(processedContent);
            const processedHTML = htmlContent.replace(/<\/p>\s*<p>/g, '</p><br><p>');
            
            return [processedHTML, headers];
        }
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
            const targetLink = this.getLinkHref(link);
            return `<a href="${targetLink}">${this.escapeHtml(link)}</a>`;
        }
        
        if (propKey.startsWith('file.')) {
            const fileProp = propKey.substring(5);
            const value = fileProps[fileProp];
            return this.escapeHtml(value || '');
        }
        
        if (propKey.startsWith('note.')) {
            if (!fileProps.notes) return '';
            
            const noteProp = propKey.substring(5);
            let noteValue = fileProps.notes[noteProp];
            console.log(noteValue)
            
            if (!noteValue) return '';
            
            if (typeof noteValue === 'string' && noteValue.startsWith('"[[') && noteValue.endsWith(']]"')) {
                const linkContent = noteValue.slice(3, -3);
                
                if (linkContent.includes('.')) {
                    const extension = linkContent.split('.').pop().toLowerCase();
                    if (this.image_types.has(extension)) {
                        const imageUrl = this.getLinkHref(linkContent);
                        if (imageUrl !== '#file-not-found') {
                            return imageUrl;
                        }
                        return '';
                    }
                }
                
                const targetUrl = this.getLinkHref(linkContent);
                if (targetUrl !== '#file-not-found') {
                    return targetUrl;
                }
                return '';
            }
            
            const processedContent = await this.processMarkdown(noteValue, link);
            return processedContent;
        }
        
        if (!fileProps.notes) return '';
        
        let noteValue = fileProps.notes[propKey];
        if (!noteValue) return '';
        
        if (typeof noteValue === 'string' && noteValue.startsWith('[[') && noteValue.endsWith(']]')) {
            const linkContent = noteValue.slice(2, -2);
            
            if (linkContent.includes('.')) {
                const extension = linkContent.split('.').pop().toLowerCase();
                if (this.image_types.has(extension)) {
                    const imageUrl = this.getLinkHref(linkContent);
                    if (imageUrl !== '#file-not-found') {
                        return imageUrl;
                    }
                    return '';
                }
            }
            
            const targetUrl = this.getLinkHref(linkContent);
            if (targetUrl !== '#file-not-found') {
                return targetUrl;
            }
            return '';
        }
        
        const processedContent = await this.processMarkdown(noteValue, link);
        return processedContent;
    }

    getSortValue(link, property) {
        const fileId = this.findFileIdByLink(link);
        if (!fileId) return '';
        
        const fileProps = fileProperties[fileId];
        if (!fileProps) return '';
        
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
        
        if (property.startsWith('note.')) {
            const noteProp = property.substring(5);
            if (!fileProps.notes) return '';
            const noteValue = fileProps.notes[noteProp];
            
            if (typeof noteValue === 'string' && noteValue.startsWith('"') && noteValue.endsWith('"')) {
                return noteValue.slice(1, -1);
            }
            
            return noteValue || '';
        }
        
        if (!fileProps.notes) return '';
        const noteValue = fileProps.notes[property];
        
        if (typeof noteValue === 'string' && noteValue.startsWith('"') && noteValue.endsWith('"')) {
            return noteValue.slice(1, -1);
        }
        
        return noteValue || '';
    }

    unescapeHtml(text) {
        return text
            .replace(/&amp;/g, "&")
            .replace(/&lt;/g, "<")
            .replace(/&gt;/g, ">")
            .replace(/&quot;/g, '"')
            .replace(/&#x27;/g, "'");
    }

    async processTransclusions(content, currentFile = null) {
        if (this.transclusion_depth >= this.max_transclusion_depth) {
            console.log('Max transclusion depth reached');
            return content;
        }

        this.transclusion_depth++;

        const transclusion_pattern = /!\[\[([^\]]+)\]\]/g;
        
        const matches = [...content.matchAll(transclusion_pattern)];
        console.log(`Found ${matches.length} transclusion(s) to process`);

        let processedContent = content;
        let totalOffset = 0;

        for (const match of matches) {
            const fullMatch = match[0];
            const link = match[1].split('|')[0];
            const matchStart = match.index + totalOffset;
            const matchEnd = matchStart + fullMatch.length;

            console.log(`Processing transclusion: ${link}`);
            const replacement = await this.processTransclusion(link, currentFile);
            
            const before = processedContent.substring(0, matchStart);
            const after = processedContent.substring(matchEnd);
            processedContent = before + replacement + after;

            totalOffset += replacement.length - fullMatch.length;
        }

        this.transclusion_depth--;
        return processedContent;
    }

    generateTransclusionId(fileName) {
        const timestamp = Date.now().toString(36);
        const nameHash = fileName.replace(/[^a-zA-Z0-9]/g, '').substring(0, 8);
        return `transcl-${nameHash}-${timestamp}`;
    }

    processTransclusionFootnotes(content, fileName) {
        const footnotes = {};
        let footnoteCounter = 1;
        const transclusionId = this.generateTransclusionId(fileName);

        let contentWithoutFootnotes = content.replace(/^\[\^([^\]]+)\]:\s*(.*)$/gm, (match, id, text) => {
            footnotes[id] = text;
            return '';
        });

        contentWithoutFootnotes = contentWithoutFootnotes.replace(/\[\^([^\]]+)\]/g, (match, id) => {
            if (footnotes.hasOwnProperty(id)) {
                const uniqueId = `${transclusionId}-${id}`;
                const tooltipContent = this.escapeTooltipContent(footnotes[id]);
                footnoteCounter++;
                return `<span class="fn"><a href="#fn-${uniqueId}" class="fn-link" id="fnref-${uniqueId}"><sup>[${id}]</sup></a><span class="fn-tooltip">${tooltipContent}</span></span>`;
            }
            return match;
        });

        let footnotesHtml = '';
        if (Object.keys(footnotes).length > 0) {
            footnotesHtml = '<div class="transclusion-footnotes"><hr class="footnote-separator"><ol class="footnote-list">';
            for (const [id, text] of Object.entries(footnotes)) {
                const uniqueId = `${transclusionId}-${id}`;
                footnotesHtml += `<li id="fn-${uniqueId}">${text} <a href="#fnref-${uniqueId}" class="footnote-backref">&#8617;</a></li>`;
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

        if (link.includes('.')) {
            const extension = link.split('.').pop().toLowerCase();
            if (this.image_types.has(extension)) {
                return this.processImageTransclusion(link);
            }
        }

        let fileName, section;
        if (link.includes('#')) {
            [fileName, section] = link.split('#', 2);
        } else {
            fileName = link;
            section = null;
        }

        let originalFileContent = this.findFileContent(fileName);
        let fileType = this.getFileType(fileName);
        
        if (!originalFileContent) {
            console.log('File not found:', fileName);
            return `> File not found: ${link}`;
        }

        if (this.processing_files.has(fileName)) {
            console.log('Circular reference detected:', fileName);
            return `> Circular reference detected: ${link}`;
        }

        this.processing_files.add(fileName);

        let processedContent;
        let footnotesHtml = '';

        try {
            if (fileType === 'canvas') {
                processedContent = await this.processCanvas(originalFileContent);
            } else if (fileType === 'base') {
                processedContent = await this.processBase(originalFileContent);
            } else {
                let fileContent;
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

                const { content: contentWithoutFootnotes, footnotesHtml: footnotes } = 
                    this.processTransclusionFootnotes(fileContent, fileName);
                footnotesHtml = footnotes;

                processedContent = await this.processTransclusions(contentWithoutFootnotes, fileName);
            }

            this.processing_files.delete(fileName);

            if (fileType === 'canvas' || fileType === 'base') {
                const headerHtml = `<span class="transcl-bar"><span><strong>${section ? `${fileName} <span class="file-link">></span> ${section}` : `${fileName}`}</strong></span> <span class="goto">[[${link}|>>]]</span></span>`;
                
                return `\n\n<blockquote class="transclusion">
    <div class="transclusion-header">${headerHtml}</div>
    <div class="transclusion-content">${processedContent}</div>
    </blockquote>\n\n`;
            } else {
                const lines = processedContent.split('\n');
                const blockquote = lines.map(line => line.trim() ? `> ${line}` : '>').join('\n');

                let result = `\n\n> <span class="transcl-bar"><span>${section ? `**${fileName}** <span class="file-link">></span> **${section}**` : `**${fileName}**`}</span> <span class="goto">[[${link}|>>]]</span></span>\n>\n${blockquote}`;

                if (footnotesHtml) {
                    result += `\n>\n> ${footnotesHtml.replace(/\n/g, '\n> ')}`;
                }

                result += '\n\n';
                return result;
            }

        } catch (error) {
            this.processing_files.delete(fileName);
            console.error('Error processing transclusion:', error);
            return `> Error processing ${link}: ${error.message}`;
        }
    }

    getFileType(fileName) {
        const fileId = this.findFileIdByLink(fileName);
        if (fileId && fileProperties[fileId]) {
            const ext = fileProperties[fileId].ext;
            if (ext === 'canvas') return 'canvas';
            if (ext === 'base') return 'base';
            if (ext === 'md') return 'markdown';
        }
        
        if (fileName.endsWith('.canvas')) return 'canvas';
        if (fileName.endsWith('.base')) return 'base';
        return 'markdown';
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
        console.log('Available files:', Object.keys(fileContentMap));
        fileName = fileName.replace(/\//g, "\\");
        
        if (fileContentMap.hasOwnProperty(fileName)) {
            console.log('Found exact match:', fileName);
            return getFile(fileName);
        }
        
        if (fileContentMap.hasOwnProperty(fileName + '.md')) {
            console.log('Found with .md extension:', fileName + '.md');
            return getFile(fileName + '.md');
        }

        const lowerFileName = fileName.toLowerCase();
        for (const [key, content] of Object.entries(fileContentMap)) {
            if (key.toLowerCase() === lowerFileName || key.toLowerCase() === lowerFileName + '.md') {
                console.log('Found case-insensitive match:', key);
                return fileContents[content];
            }
        }

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

        if (sectionName.startsWith('^')) {
            const blockId = sectionName.substring(1);
            const blockContent = this.extractBlockContent(fullContent, blockId);
            if (blockContent) {
                return this.collectFootnotesForContent(blockContent, fullContent);
            }
            return null;
        }

        const sectionContent = this.extractSection(fullContent, sectionName);
        if (!sectionContent) {
            return null;
        }

        return this.collectFootnotesForContent(sectionContent, fullContent);
    }

    collectFootnotesForContent(content, fullContent) {
        const footnoteRefs = new Set();
        const refMatches = content.matchAll(/\[\^([^\]]+)\]/g);

        for (const match of refMatches) {
            footnoteRefs.add(match[1]);
        }

        if (footnoteRefs.size === 0) {
            return content;
        }

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

        if (footnoteDefinitions.length > 0) {
            return content + '\n\n' + footnoteDefinitions.join('\n');
        }

        return content;
    }

    extractSection(content, sectionName) {
        console.log('Extracting section:', sectionName);

        if (sectionName.startsWith('^')) {
            const blockId = sectionName.substring(1);
            return this.extractBlockContent(content, blockId);
        }

        const lines = content.split('\n');
        const sectionLines = [];
        let inSection = false;
        let sectionLevel = 0;

        const sectionSlug = slugify(sectionName);
        console.log('Looking for section slug:', sectionSlug);

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.trim().startsWith('#')) {
                const headerMatch = line.match(/^(#+)\s*(.*)$/);
                if (headerMatch) {
                    const currentLevel = headerMatch[1].length;
                    const currentHeader = headerMatch[2].trim();
                    const currentSlug = slugify(currentHeader);

                    console.log(`Found header: "${currentHeader}" (slug: "${currentSlug}") at level ${currentLevel}`);

                    if (currentSlug === sectionSlug || currentHeader.toLowerCase() === sectionName.toLowerCase()) {
                        console.log('Section found!');
                        inSection = true;
                        sectionLevel = currentLevel;
                        sectionLines.push(line);
                    } else if (inSection && currentLevel <= sectionLevel) {
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

    extractBlockContent(content, blockId) {
        const lines = content.split('\n');
        let blockRefLine = null;

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

        const refLine = lines[blockRefLine].trim();
        const hasContentOnSameLine = refLine !== `^${blockId}` && refLine.replace(`^${blockId}`, '').trim();

        if (hasContentOnSameLine) {
            const [start, end] = this.findParagraphBoundaries(lines, blockRefLine);
            if (start !== null) {
                const paragraphLines = lines.slice(start, end + 1);
                const relativeRefLine = blockRefLine - start;
                paragraphLines[relativeRefLine] = paragraphLines[relativeRefLine].replace(`^${blockId}`, '').trim();
                return paragraphLines.join('\n');
            }
            return refLine.replace(`^${blockId}`, '').trim();
        }

        let contentEnd = blockRefLine - 1;

        while (contentEnd >= 0 && !lines[contentEnd].trim()) {
            contentEnd--;
        }

        if (contentEnd < 0) {
            return null;
        }

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
        let target = (fileLinks[fileName] || fileLinks[fileName + '.md'] || '#file-not-found')
            .replace(/\\/g, '/')
            .replace(/\.md$/i, '.html');
        
        if (target === '#file-not-found'){
            console.log(fileName)
        }

        console.log("Target:", target);

        const article = document.querySelector("article");
        const attributeValue = article.getAttribute('data-current-file');
        let relCurParts = attributeValue.replace(/\\/g, '/').replace(' ', '-').toLowerCase().split('/').slice(0, -1)

        let relTgtParts = target.split('/').filter(Boolean);
        console.log(relTgtParts)

        let i = 0;
        while (i < relCurParts.length && i < relTgtParts.length && relCurParts[i] === relTgtParts[i]) {
            i++;
        }

        const relativePath = [...Array(relCurParts.length - i).fill('..'), ...relTgtParts.slice(i)].join('/');

        console.log("Relative path:", relativePath);

        return relativePath.replace(/ /g, '-');
    }

    findFileIdByLink(link) {
        if (fileContentMap[link]) {
            return fileContentMap[link];
        }
        
        if (!link.includes('.') && fileContentMap[link + '.md']) {
            return fileContentMap[link + '.md'];
        }
        
        for (const [fileId, props] of Object.entries(fileProperties)) {
            if (props.file) {
                if (props.file === link) {
                    return fileId;
                }
                
                const basename = props.file.replace(/\.[^/.]+$/, "");
                if (basename === link) {
                    return fileId;
                }
            }
        }
        
        return null;
    }

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
                footnotesHtml += `<li id="fn-${id}">${text} <a href="#fnref-${id}" class="footnote-backref">&#8617;</a></li>`;
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

    preprocessHeaders(content) {
        const lines = content.split('\n');
        const processedLines = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmedLine = line.trim();
            
            if (trimmedLine.match(/^#{1,6}\s+.+/)) {
                const prevLine = i > 0 ? lines[i - 1].trim() : '';
                
                if (prevLine && !prevLine.startsWith('#') && processedLines.length > 0) {
                    if (processedLines[processedLines.length - 1].trim() !== '') {
                        processedLines.push('');
                    }
                }
                processedLines.push(line);
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
                    const headerId = slugify(headerText);
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

    generateFileTreeHTML() {
        let ret_str = '';
        let checkboxPrefix = 1;
        
        const fileTuples = Object.entries(fileLinks).sort((a, b) => {
            const aPath = a[1];
            const bPath = b[1];
            
            const aLastSlash = aPath.lastIndexOf("\\");
            const bLastSlash = bPath.lastIndexOf("\\");
            
            const aDirFile = aLastSlash >= 0 ? [aPath.substring(0, aLastSlash), aPath.substring(aLastSlash + 1)] : ["", aPath];
            const bDirFile = bLastSlash >= 0 ? [bPath.substring(0, bLastSlash), bPath.substring(bLastSlash + 1)] : ["", bPath];
            
            if (aDirFile[0] !== bDirFile[0]) return aDirFile[0].localeCompare(bDirFile[0]);
            return aDirFile[1].localeCompare(bDirFile[1]);
        });
        
        for (let i = 0; i < fileTuples.length; i++) {
            const [link, filepath] = fileTuples[i];
            
            if (i === 0 || (i > 0 && fileTuples[i-1][1] !== filepath)) {
                const offsetLink = this.getLinkHref(link);
                
                if (i > 0) {
                    const prevLastSlash = fileTuples[i-1][1].lastIndexOf("\\");
                    const currLastSlash = filepath.lastIndexOf("\\");
                    
                    let prevDir = prevLastSlash >= 0 ? fileTuples[i-1][1].substring(0, prevLastSlash) : "";
                    let currDir = currLastSlash >= 0 ? filepath.substring(0, currLastSlash) : "";
                    
                    prevDir = prevDir.startsWith(".\\") && prevDir.length > 2 ? prevDir.substring(2) : "";
                    currDir = currDir.startsWith(".\\") && currDir.length > 2 ? currDir.substring(2) : "";
                    
                    if (prevDir !== currDir) {
                        let fileprev = prevDir ? prevDir + "\\" : "";
                        let filecur = currDir ? currDir + "\\" : "";
                        
                        while (fileprev !== "" && filecur !== "") {
                            const prevFirstSlash = fileprev.indexOf("\\");
                            const curFirstSlash = filecur.indexOf("\\");
                            
                            if (prevFirstSlash === -1 || curFirstSlash === -1) break;
                            
                            const prevFirst = fileprev.substring(0, prevFirstSlash);
                            const curFirst = filecur.substring(0, curFirstSlash);
                            
                            if (prevFirst !== curFirst) {
                                break;
                            }
                            
                            fileprev = fileprev.substring(prevFirstSlash + 1);
                            filecur = filecur.substring(curFirstSlash + 1);
                        }
                        
                        if (fileprev !== "" && fileprev !== "\\") {
                            const closingCount = (fileprev.match(/\\/g) || []).length;
                            ret_str += ("</ul></li>").repeat(closingCount);
                        }
                        
                        if (filecur !== "" && filecur !== "\\") {
                            const filecurElems = filecur.split("\\").filter(elem => elem !== "");
                            
                            for (let j = 0; j < filecurElems.length; j++) {
                                ret_str += '<li class="parent">\n';
                                const checkboxTag = `checkbox-${checkboxPrefix}-${filecurElems[j].replace(/\s+/g, "-")}`;
                                checkboxPrefix += 1;
                                ret_str += `<input type="checkbox" id="${checkboxTag}" name="${checkboxTag}">\n`;
                                ret_str += `<label class="checkbox" for="${checkboxTag}">${filecurElems[j].charAt(0).toUpperCase() + filecurElems[j].slice(1)}</label>\n`;
                                ret_str += '<ul class="child">\n';
                            }
                        }
                    }
                } else {
                    const firstLastSlash = filepath.lastIndexOf("\\");
                    if (firstLastSlash >= 0) {
                        let firstDir = filepath.substring(0, firstLastSlash);
                        
                        firstDir = firstDir.startsWith(".\\") && firstDir.length > 2 ? firstDir.substring(2) : "";
                        
                        if (firstDir !== "") {
                            const dirParts = firstDir.split("\\").filter(part => part !== "");
                            for (let j = 0; j < dirParts.length; j++) {
                                ret_str += '<li class="parent">\n';
                                const checkboxTag = `checkbox-${checkboxPrefix}-${dirParts[j].replace(/\s+/g, "-")}`;
                                checkboxPrefix += 1;
                                ret_str += `<input type="checkbox" id="${checkboxTag}" name="${checkboxTag}">\n`;
                                ret_str += `<label class="checkbox" for="${checkboxTag}">${dirParts[j].charAt(0).toUpperCase() + dirParts[j].slice(1)}</label>\n`;
                                ret_str += '<ul class="child">\n';
                            }
                        }
                    }
                }
                const fileName = link.split('/').pop().replace(/\.md$/i, '');
                ret_str += '<li>' + `<a href="${offsetLink}">${fileName}</a>` + '</li>';
            }
        }
        return "<div id=\"idk\"><ul class=\"menu\">" + ret_str + "</ul></div>";
    }

    generateSearchBarHTML() {
        const searchDict = {};
        const seenValues = new Set();
        
        for (const [key, value] of Object.entries(fileLinks)) {
            if (!seenValues.has(value)) {
                searchDict[key] = value;
                seenValues.add(value);
            }
        }
        
        let searchHtml = '<input type="text" id="searchInput" onkeyup="searchForArticle()" placeholder="Search..">';
        searchHtml += '<ul id="articles">';
        
        for (const [key, value] of Object.entries(searchDict)) {
            const rightPartLink = value.substring(1).replace(/ /g, "-");
            const link = this.getLinkHref(key);
            const displayPath = rightPartLink.substring(1).replace(/\\/g, " > ");
            const fileName = key.split('/').pop();
            
            searchHtml += `<li><a searchText="${link}" href="${link}">${fileName}<br><sub class="fileloc">${displayPath}</sub></a></li>`;
        }
        
        searchHtml += '</ul>';
        return searchHtml;
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

function slugify(text) {
    if (!text) return '';
    return text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '') // Normalize accented chars (NFKD), remove diacritics
    .trim().toLowerCase() // Trim, lowercase
    .replace(/[^a-z0-9 \-()†]/g, '') // Remove characters that are not alphanumeric, space, or hyphen
    .replace(/\s+/g, '-') // Replace spaces (one or more) with a hyphen
    .replace(/-+/g, '-') // Collapse multiple hyphens
    .replace(/^-+/, '').replace(/-+$/, ''); // Remove leading/trailing hyphens
}

marked.setOptions({
    breaks: true,
    gfm: true,
    tables: true,
    headerIds: true,
    headerPrefix: '',
    pedantic: false,
    sanitize: false,
    smartLists: true,
    smartypants: false
});

const renderer = new marked.Renderer();
renderer.heading = function(text, level, raw) {
    const escapedText = slugify(text);
    return `<h${level} id="${escapedText}">${text}</h${level}>`;
};
marked.setOptions({ renderer: renderer });

async function renderContent() {
    const article = document.querySelector("article");

    const processor = new ObsidianProcessor();

    try {
        const fileType = article.getAttribute('data-type');
        const attributeValue = article.getAttribute('data-current-file');
        const content = getFile(attributeValue);
        
        const [processedHTML, headers] = await processor.processFile(content, fileType);

        const searchBarHtml = processor.generateSearchBarHTML();
        document.getElementById("searchbar").innerHTML = searchBarHtml;
        if (headers.length > 0) {
            const tocHtml = processor.buildTableOfContents(headers);
            document.getElementById('toc-content').innerHTML = tocHtml;
            document.getElementById('table-of-contents').style.removeProperty('display');
        }
        document.getElementById("navbar").innerHTML = processor.generateFileTreeHTML();
        article.innerHTML = processedHTML
    } catch (error) {
        console.error('Error processing content:', error);
        article.innerHTML = '<p>Error processing content. Please check the console for details.</p>';
    }
}

document.addEventListener('DOMContentLoaded', renderContent);

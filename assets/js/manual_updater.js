document.body.addEventListener('htmx:wsAfterMessage', function (evt) {
    const html = evt.detail.message;
    if (html.includes('<template')) { handleTemplateFragments(html); }
});

function handleTemplateFragments(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const templates = doc.querySelectorAll('template');
    templates.forEach(template_tag => {
        const extSel = template_tag.getAttribute('data-manual-update') || template_tag.getAttribute('hx-swap-oob');
        if (!extSel) return;
        const nodes = Array.from(template_tag.content.childNodes).filter(n => n.nodeType === Node.ELEMENT_NODE);
        nodes.forEach(node => manualUpdate(node, extSel));
    });
}

function manualUpdate(node, extSel) {
    const [position, selector] = extSel.split(/:(.+)/);
    const container = document.querySelector(selector);
    if (!container) {
        console.error('manualUpdate: container not found for', selector);
        return;
    }
    const clone = node.cloneNode(true);
    switch (position) {
        case 'beforebegin': container.before(clone); break;
        case 'afterend': container.after(clone); break;
        case 'afterbegin': container.prepend(clone); break;
        case 'beforeend': container.append(clone); break;
        case 'replace': container.replaceWith(clone); break;
        default:
            console.warn('manualUpdate: unknown position', position);
    }
}



// Async METHOD to API
async function METHOD(method = 'POST', url = '', data) {
    let payload = {
        method: method,
        mode: 'cors',
        cache: 'no-cache',
        credentials: 'same-origin',
        headers: data ? {
            'Content-Type': 'application/json'
        } : {},
        redirect: 'follow',
        referrerPolicy: 'no-referrer'
    }
    if (data) {
        payload.body = JSON.stringify(data);
    }
    try {
        const response = await fetch(url, payload).catch( (e) => {throw e});
        if (response.ok !== true) throw `HTTP Error ${response.status}: ${response.statusText}`
        let js = response.json();
        return js
    } catch (e) {
        alert(e);
    }
}

// HTTP methods
let DELETE = (url, data) => METHOD('DELETE', url, data);
let GET = (url, data) => METHOD('GET', url, data);
let PATCH = (url, data) => METHOD('PATCH', url, data);
let POST = (url, data) => METHOD('POST', url, data);
let PUT = (url, data) => METHOD('PUT', url, data);


// Prettifier for large numbers (adds commas)
Number.prototype.pretty = function(fix) {
    if (fix) {
        return String(this.toFixed(fix)).replace(/(\d)(?=(\d{3})+\.)/g, '$1,');
    }
    return String(this.toFixed(0)).replace(/(\d)(?=(\d{3})+$)/g, '$1,');
};

// HTML shortcuts
let htmlobj = (type, text) => { let obj = document.createElement(type); obj.innerText = text ? text : ""; return obj }
let _h1 = (title) => htmlobj('h1', title);
let _h2 = (title) => htmlobj('h2', title);
let _span = (title) => htmlobj('span', title);
let _p = (title) => htmlobj('p', title);
let _br = (title) => htmlobj('br');
let _hr = (title) => htmlobj('hr');
let _tr = () => htmlobj('tr');
let _td = (title) => htmlobj('td', title);
let _th = (title, width) => { let obj = htmlobj('th', title); if (width) obj.style.width = width + "px"; return obj }
let _table = () => htmlobj('table');



async function prime_frontpage() {
    let all = await GET("all");
    let main = document.getElementById('main');
    main.innerHTML = "";
    let block_count = all.block.length.pretty();
    let h1 = _h1(`Recent activity (${block_count} blocks in total)`);
    main.appendChild(h1);
    all.block.sort((a,b) => b.timestamp - a.timestamp);  // sort desc by timestamp


    // Recent blocks
    let activity_table = _table();
    activity_table.style.tableLayout = 'fixed';
    main.appendChild(activity_table);

    let theader = _tr();
    theader.appendChild(_th('Source IP', 300));
    theader.appendChild(_th('Added', 120));
    theader.appendChild(_th('Expires', 120));
    theader.appendChild(_th('Reason', 500));
    theader.appendChild(_th('Actions', 100));
    activity_table.appendChild(theader);

    let results_shown = 0;
    for (const entry of all.block) {
        let tr = _tr();
        let td_ip = _td(entry.ip);
        td_ip.style.fontFamily = "monospace";
        if (entry.ip.length > 16) td_ip.style.fontSize = "0.8rem";
        let td_added = _td(moment(entry.timestamp*1000.0).fromNow());
        let td_expires = _td(entry.expires > 0 ? moment(entry.expires*1000.0).fromNow() : 'Never');
        let td_reason = _td(entry.reason);
        let td_action = _td();
        tr.appendChild(td_ip);
        tr.appendChild(td_added);
        tr.appendChild(td_expires);
        tr.appendChild(td_reason);
        tr.appendChild(td_action);
        activity_table.appendChild(tr);
        results_shown++;
        if (results_shown > 25 && results.block.length > 25) {
            break
        }
    }
    if (results_shown === 0) {
        let tr = _tr();
        tr.innerText = "No activity found...";
        activity_table.appendChild(_tr);
    }


}


async function prime_search(target, state) {
    if (!state) {
        window.history.pushState({}, '', `?search:${target}`);
    }
    let main = document.getElementById('main');
    main.innerHTML = '';
    let title = _h1("Search results for " + target + ":");
    main.appendChild(title);
    let p = _p("Searching, please wait...");
    main.appendChild(p);

    let results = {};
    if (target && target.length > 0) {
        results = await POST('search', {source: target});
        main.removeChild(p);


        // Allow list results
        let h2 = _h2(`Allow list results (${results.allow.length})`);
        main.appendChild(h2);
        let allow_table = _table();
        allow_table.style.tableLayout = 'fixed';
        main.appendChild(allow_table);

        let theader = _tr();
        theader.appendChild(_th('Source IP', 300));
        theader.appendChild(_th('Added', 120));
        theader.appendChild(_th('Expires', 120));
        theader.appendChild(_th('Reason', 500));
        theader.appendChild(_th('Actions', 100));
        allow_table.appendChild(theader);

        let results_shown = 0;
        results.allow.sort((a,b) => b.timestamp - a.timestamp);  // sort desc by timestamp
        for (const entry of results.allow) {
            let tr = _tr();
            let td_ip = _td(entry.ip);
            let td_added = _td(moment(entry.timestamp * 1000.0).fromNow());
            let td_expires = _td(entry.expires > 0 ? moment(entry.expires * 1000.0).fromNow() : 'Never');
            let td_reason = _td(entry.reason);
            let td_action = _td();
            td_ip.style.fontFamily = "monospace";
            if (entry.ip.length > 16) td_ip.style.fontSize = "0.8rem";
            tr.appendChild(td_ip);
            tr.appendChild(td_added);
            tr.appendChild(td_expires);
            tr.appendChild(td_reason);
            tr.appendChild(td_action);
            allow_table.appendChild(tr);
            results_shown++;
            if (results_shown > 25 && results.block.length > 25) {
                break
            }
        }
        if (results_shown === 0) {
            let tr = _tr();
            tr.innerText = "No results found...";
            allow_table.appendChild(tr);
        }

        // Block list results
        let bh2 = _h2(`Block list results (${results.block.length})`);
        main.appendChild(bh2);
        let block_table = _table();
        block_table.style.tableLayout = 'fixed';
        main.appendChild(block_table);

        let btheader = _tr();
        btheader.appendChild(_th('Source IP', 300));
        btheader.appendChild(_th('Added', 120));
        btheader.appendChild(_th('Expires', 120));
        btheader.appendChild(_th('Reason', 500));
        btheader.appendChild(_th('Actions', 100));
        block_table.appendChild(btheader);

        results_shown = 0;
        results.block.sort((a,b) => b.timestamp - a.timestamp);  // sort desc by timestamp
        for (const entry of results.block) {
            let tr = _tr();
            let td_ip = _td(entry.ip);
            let td_added = _td(moment(entry.timestamp * 1000.0).fromNow());
            let td_expires = _td(entry.expires > 0 ? moment(entry.expires * 1000.0).fromNow() : 'Never');
            let td_reason = _td(entry.reason);
            let td_actions = _td('');
            td_ip.style.fontFamily = "monospace";
            if (entry.ip.length > 16) td_ip.style.fontSize = "0.8rem";
            tr.appendChild(td_ip);
            tr.appendChild(td_added);
            tr.appendChild(td_expires);
            tr.appendChild(td_reason);
            tr.appendChild(td_actions);

            block_table.appendChild(tr);
            results_shown++;
            if (results_shown > 25 && results.block.length > 25) {
                break
            }
        }
        if (results_shown === 0) {
            let tr = _tr();
            tr.innerText = "No results found...";
            block_table.appendChild(tr);
        }

        // iptables results
        let ih2 = _h2(`Local iptables results (${results.iptables.length})`);
        main.appendChild(ih2);
        let iptables_table = _table();
        iptables_table.style.tableLayout = 'fixed';
        main.appendChild(iptables_table);

        let itheader = _tr();
        itheader.appendChild(_th('Source IP', 300));
        itheader.appendChild(_th('Host', 200));
        itheader.appendChild(_th('Chain', 100));
        itheader.appendChild(_th('Reason', 450));
        itheader.appendChild(_th('Actions', 100));
        iptables_table.appendChild(itheader);

        results_shown = 0;
        for (const entry of results.iptables) {
            let tr = _tr();
            let td_ip = _td(entry.source);
            let td_host = _td(entry.hostname);
            let td_chain = _td(entry.chain);
            let td_reason = _td(entry.extensions.replace(/\/\*\s*(.+)\s*\*\//, (b,a) => a));
            let td_actions = _td('');
            td_ip.style.fontFamily = "monospace";
            if (entry.source.length > 16) td_ip.style.fontSize = "0.8rem";
            tr.appendChild(td_ip);
            tr.appendChild(td_host);
            tr.appendChild(td_chain);
            tr.appendChild(td_reason);
            tr.appendChild(td_actions);

            iptables_table.appendChild(tr);
            results_shown++;
            if (results_shown > 25 && results.block.length > 25) {
                break
            }
        }
        if (results_shown === 0) {
            let tr = _tr();
            tr.innerText = "No results found...";
            iptables_table.appendChild(tr);
        }

    } else {
        main.innerText = "Use the search bar in the top left corner for now...";
    }

}


let actions = {
    frontpage: prime_frontpage,
    search: prime_search
};


async function prime(args) {
    console.log(args);
    let segs = location.search.substr(1).match(/^([a-z]*):?(.*)$/);
    let action = segs[1];
    let params = segs[2];
    action_call = actions[action] ? actions[action] : actions['frontpage'];
    await action_call(params, args ? args.state : null);
}

window.onpopstate = prime;

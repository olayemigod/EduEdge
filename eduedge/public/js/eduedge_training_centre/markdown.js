function escapeHtml(value) {
	return String(value ?? "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
}

function safeHref(value) {
	const href = String(value || "").trim();
	if (/^training-module:[a-z0-9][a-z0-9_-]*(#[a-z0-9_.:-]+)?$/i.test(href)) return href;
	if (/^\/app\/[a-z0-9/_?=&%.-]+$/i.test(href)) return href;
	if (/^https:\/\//i.test(href)) return href;
	return "#";
}

function inline(text) {
	return escapeHtml(text)
		.replace(/`([^`]+)`/g, "<code>$1</code>")
		.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
		.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, label, href) => {
			const safe = safeHref(href);
			if (safe.startsWith("training-module:")) {
				const moduleId = safe.slice("training-module:".length).split("#", 1)[0];
				return `<a href="#" data-training-module="${escapeHtml(moduleId)}">${label}</a>`;
			}
			const external = safe.startsWith("https://") ? ' target="_blank" rel="noopener noreferrer"' : "";
			return `<a href="${escapeHtml(safe)}"${external}>${label}</a>`;
		});
}

function renderTable(lines) {
	const split = (row) => row.split("|").slice(1, -1).map((cell) => cell.trim());
	const header = split(lines[0]);
	const rows = lines.slice(2).map(split);
	return `<div class="edge-training-table-wrap"><table class="edge-training-table"><thead><tr>${header
		.map((cell) => `<th>${inline(cell)}</th>`)
		.join("")}</tr></thead><tbody>${rows
		.map((row) => `<tr>${row.map((cell) => `<td>${inline(cell)}</td>`).join("")}</tr>`)
		.join("")}</tbody></table></div>`;
}

function renderLine(line) {
	const heading = line.match(/^(#{1,6})\s+(.+)$/);
	if (heading) {
		const level = Math.min(6, heading[1].length + 1);
		return `<h${level}>${inline(heading[2])}</h${level}>`;
	}
	const quote = line.match(/^>\s?(.*)$/);
	if (quote) return `<blockquote>${inline(quote[1])}</blockquote>`;
	const checklist = line.match(/^-\s+\[( |x|X)\]\s+(.+)$/);
	if (checklist) {
		return `<div class="edge-training-guide-check"><input type="checkbox" disabled ${
			checklist[1].toLowerCase() === "x" ? "checked" : ""
		}> <span>${inline(checklist[2])}</span></div>`;
	}
	const bullet = line.match(/^-\s+(.+)$/);
	if (bullet) return `<div class="edge-training-guide-bullet"><span>•</span><span>${inline(bullet[1])}</span></div>`;
	const numbered = line.match(/^(\d+)\.\s+(.+)$/);
	if (numbered) {
		return `<div class="edge-training-guide-number"><strong>${numbered[1]}.</strong><span>${inline(numbered[2])}</span></div>`;
	}
	return `<p>${inline(line)}</p>`;
}

export function renderTrainingMarkdown(markdown) {
	const lines = String(markdown || "").split("\n");
	const blocks = [];
	let inCode = false;
	let codeLanguage = "";
	let codeLines = [];
	for (let index = 0; index < lines.length; index += 1) {
		const line = lines[index];
		const fence = line.match(/^```(.*)$/);
		if (fence) {
			if (inCode) {
				blocks.push(
					`<pre><code class="language-${escapeHtml(codeLanguage)}">${escapeHtml(codeLines.join("\n"))}</code></pre>`,
				);
				inCode = false;
				codeLanguage = "";
				codeLines = [];
			} else {
				inCode = true;
				codeLanguage = String(fence[1] || "").trim();
			}
			continue;
		}
		if (inCode) {
			codeLines.push(line);
			continue;
		}
		if (!line.trim()) {
			blocks.push("");
			continue;
		}
		if (line.startsWith("|") && lines[index + 1] && /^\|\s*:?-{3,}/.test(lines[index + 1])) {
			const tableLines = [line, lines[index + 1]];
			index += 2;
			while (index < lines.length && lines[index].startsWith("|")) {
				tableLines.push(lines[index]);
				index += 1;
			}
			index -= 1;
			blocks.push(renderTable(tableLines));
			continue;
		}
		blocks.push(renderLine(line));
	}
	if (inCode) {
		blocks.push(`<pre><code class="language-${escapeHtml(codeLanguage)}">${escapeHtml(codeLines.join("\n"))}</code></pre>`);
	}
	return `<div class="edge-training-markdown">${blocks.join("\n")}</div>`;
}

function parseFlowchart(source) {
	const lines = String(source || "").split("\n").map((line) => line.trim()).filter(Boolean);
	const header = lines.shift() || "";
	const headerMatch = header.match(/^(?:flowchart|graph)\s+(TD|TB|BT|LR|RL)$/i);
	if (!headerMatch) return null;
	const direction = headerMatch[1].toUpperCase();
	const nodes = new Map();
	const edges = [];
	const nodePattern = /([A-Za-z0-9_]+)(?:\[([^\]]+)\]|\{([^}]+)\})?/g;
	const ensureNode = (match) => {
		if (!match) return "";
		const id = match[1];
		const existing = nodes.get(id) || {};
		nodes.set(id, {
			id,
			label: String(match[2] || match[3] || existing.label || id).trim(),
			decision: Boolean(match[3]) || existing.decision,
		});
		return id;
	};
	lines.forEach((line) => {
		if (line.startsWith("%%")) return;
		const parts = line.split(/-->|---/).map((part) => part.replace(/^\|[^|]*\|/, "").trim()).filter(Boolean);
		if (parts.length < 2) return;
		const ids = parts.map((part) => {
			const matches = [...part.matchAll(nodePattern)];
			return ensureNode(matches[matches.length - 1]);
		}).filter(Boolean);
		for (let index = 0; index < ids.length - 1; index += 1) edges.push([ids[index], ids[index + 1]]);
	});
	if (!nodes.size || !edges.length) return null;
	const order = [];
	const seen = new Set();
	edges.flat().forEach((id) => {
		if (!seen.has(id) && nodes.has(id)) {
			seen.add(id);
			order.push(nodes.get(id));
		}
	});
	nodes.forEach((node, id) => {
		if (!seen.has(id)) order.push(node);
	});
	return { direction, nodes: order };
}

export function renderTrainingFlowcharts(root) {
	if (!root) return;
	root.querySelectorAll('pre code.language-mermaid, pre code.lang-mermaid').forEach((code) => {
		const parsed = parseFlowchart(code.textContent || "");
		const pre = code.closest("pre");
		if (!parsed || !pre) return;
		const flow = document.createElement("div");
		flow.className = `edge-training-flow edge-training-flow--${parsed.direction.toLowerCase()}`;
		parsed.nodes.forEach((node, index) => {
			const card = document.createElement("div");
			card.className = `edge-training-flow__node${node.decision ? " is-decision" : ""}`;
			card.textContent = node.label;
			flow.appendChild(card);
			if (index < parsed.nodes.length - 1) {
				const arrow = document.createElement("div");
				arrow.className = "edge-training-flow__arrow";
				arrow.textContent = ["LR", "RL"].includes(parsed.direction) ? "→" : "↓";
				flow.appendChild(arrow);
			}
		});
		pre.replaceWith(flow);
	});
}

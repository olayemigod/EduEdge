(() => {
	const root = document.getElementById("results-content");
	const status = document.getElementById("results-status");
	const detail = document.getElementById("results-detail");
	if (!root || !status || !detail) return;

	const esc = (value) => String(value ?? "")
		.replaceAll("&", "&amp;")
		.replaceAll("<", "&lt;")
		.replaceAll(">", "&gt;")
		.replaceAll('"', "&quot;")
		.replaceAll("'", "&#039;");

	const percent = (value) => {
		const number = Number(value);
		return Number.isFinite(number) ? `${number.toFixed(2)}%` : "-";
	};

	const downloadUrl = (publication, student) => {
		const query = new URLSearchParams({ publication, student });
		return `/api/method/eduedge.api.results_portal.download_my_result?${query.toString()}`;
	};

	const resultCard = (result, student) => {
		const summary = result.summary || {};
		const title = summary.result_mode === "Annual"
			? "Annual Result"
			: (summary.academic_term_label || "Terminal Result");
		return `
			<article class="result-card">
				<div class="result-card-head">
					<div>
						<p class="result-mode">${esc(title)}</p>
						<h3>${esc(result.academic_year || "")}</h3>
						<p>${esc(summary.institution_name || "")}${summary.branch_name ? ` · ${esc(summary.branch_name)}` : ""}</p>
					</div>
					<span class="result-issued">Issue v${esc(result.issue_version || 1)}</span>
				</div>
				<div class="result-metrics">
					<div><span>Average</span><strong>${percent(summary.average_percent)}</strong></div>
					<div><span>Grade</span><strong>${esc(summary.overall_grade || "-")}</strong></div>
					<div><span>Attendance</span><strong>${percent(summary.attendance_percent)}</strong></div>
					<div><span>Subjects</span><strong>${esc(summary.course_count ?? "-")}</strong></div>
				</div>
				${summary.overall_remark ? `<p class="result-remark">${esc(summary.overall_remark)}</p>` : ""}
				<div class="result-actions">
					<button type="button" class="result-button result-button-secondary" data-view-result data-publication="${esc(result.result_publication)}" data-student="${esc(student.name)}">View result</button>
					<a class="result-button" href="${downloadUrl(result.result_publication, student.name)}">Download official PDF</a>
				</div>
			</article>
		`;
	};

	const studentPanel = (student, index) => {
		const results = student.results || [];
		return `
			<section class="student-results">
				<div class="student-head">
					<div class="student-avatar">
						${student.image ? `<img src="${esc(student.image)}" alt="">` : esc((student.student_name || "S").slice(0, 1))}
					</div>
					<div>
						<p class="student-relation">${esc(student.relationship || "Student")}</p>
						<h2>${esc(student.student_name || student.name)}</h2>
						<p>${esc(student.name)}</p>
					</div>
				</div>
				${results.length
					? `<div class="result-grid">${results.map((result) => resultCard(result, student)).join("")}</div>`
					: `<div class="results-empty">No approved issued report cards are available yet.</div>`
				}
			</section>
		`;
	};

	const componentText = (component) => {
		if (component?.display_value !== undefined && component?.display_value !== null) return component.display_value;
		if (!Number(component?.maximum_score || 0)) return "-";
		return Number(component?.score || 0).toFixed(2).replace(/\.00$/, "");
	};

	const courseDetail = (course, summary) => {
		const mode = summary.result_mode || "Terminal";
		let breakdown = "";
		if (mode === "Annual") {
			breakdown = (course.periods || []).map((period) =>
				`<span><strong>${esc(period.display_label || period.academic_term)}</strong>: ${percent(period.percentage)}</span>`
			).join("");
		} else {
			breakdown = (course.display_components || []).map((component) =>
				`<span><strong>${esc(component.component_label)}</strong>: ${esc(componentText(component))}</span>`
			).join("");
		}
		const total = mode === "Annual" ? course.cumulative_score : course.total_score;
		const scorePercent = mode === "Annual" ? course.annual_percentage : course.percentage;
		const metrics = (course.metrics || []).map((metric) =>
			`<span><strong>${esc(metric.display_label)}</strong>: ${esc(metric.display_value ?? "-")}</span>`
		).join("");
		return `
			<tr>
				<td><strong>${esc(course.course_name || course.course)}</strong><div class="subject-breakdown">${breakdown}</div></td>
				<td>${esc(total ?? "-")}</td>
				<td>${percent(scorePercent)}</td>
				<td>${esc(course.grade || "-")}</td>
				<td>${esc(course.remark || "-")}</td>
				<td><div class="subject-breakdown">${metrics || "-"}</div></td>
			</tr>
		`;
	};

	const renderDetail = (payload) => {
		const summary = payload.summary || {};
		const review = payload.review || {};
		const issue = payload.issue_record || payload.issue || {};
		const student = payload.student || {};
		const courses = summary.courses || [];
		detail.hidden = false;
		detail.innerHTML = `
			<div class="results-detail-head">
				<div>
					<p class="results-eyebrow">Official issued result · Issue v${esc(issue.issue_version || 1)}</p>
					<h2>${esc(student.student_name || student.name)}</h2>
					<p>${esc(summary.academic_term_label || summary.result_mode || "")} · ${esc(summary.academic_year || "")}</p>
				</div>
				<button type="button" class="result-close" data-close-detail aria-label="Close result details">×</button>
			</div>
			<div class="result-metrics result-detail-metrics">
				<div><span>Overall</span><strong>${percent(summary.average_percent)}</strong></div>
				<div><span>Grade</span><strong>${esc(summary.overall_grade || "-")}</strong></div>
				<div><span>Attendance</span><strong>${percent(summary.attendance_percent)}</strong></div>
				<div><span>School Opened</span><strong>${esc(summary.attendance_school_opened ?? summary.attendance_total ?? "-")}</strong></div>
			</div>
			<div class="result-detail-table-wrap">
				<table class="result-detail-table">
					<thead><tr><th>Subject</th><th>Total</th><th>%</th><th>Grade</th><th>Remark</th><th>Class Metrics</th></tr></thead>
					<tbody>${courses.map((course) => courseDetail(course, summary)).join("")}</tbody>
				</table>
			</div>
			<div class="result-comments">
				<div><span>Class Teacher</span><p>${esc(review.class_teacher_comment || "-")}</p></div>
				<div><span>Principal</span><p>${esc(review.principal_comment || "-")}</p></div>
				<div><span>Progression</span><p>${esc(review.progression_recommendation || summary.suggested_progression || "Pending Review")}</p></div>
			</div>
			<div class="result-actions">
				<a class="result-button" href="${downloadUrl(payload.publication?.name, student.name)}">Download official PDF</a>
			</div>
		`;
		detail.scrollIntoView({ behavior: "smooth", block: "start" });
	};

	async function openResult(publication, student) {
		detail.hidden = false;
		detail.innerHTML = '<div class="results-status">Loading issued result…</div>';
		try {
			const query = new URLSearchParams({ publication, student });
			const response = await fetch(`/api/method/eduedge.api.results_portal.get_my_result?${query.toString()}`, {
				credentials: "same-origin",
				headers: { "Accept": "application/json" },
			});
			if (!response.ok) throw new Error("Result details could not be loaded.");
			const body = await response.json();
			renderDetail(body.message || {});
		} catch (error) {
			detail.innerHTML = `<div class="results-status is-error">${esc(error?.message || "Result details could not be loaded.")}</div>`;
		}
	}

	root.addEventListener("click", (event) => {
		const button = event.target.closest("[data-view-result]");
		if (!button) return;
		openResult(button.dataset.publication, button.dataset.student);
	});
	detail.addEventListener("click", (event) => {
		if (!event.target.closest("[data-close-detail]")) return;
		detail.hidden = true;
		detail.replaceChildren();
	});

	async function load() {
		try {
			const response = await fetch("/api/method/eduedge.api.results_portal.get_my_results_context", {
				credentials: "same-origin",
				headers: { "Accept": "application/json" },
			});
			if (!response.ok) throw new Error("Results could not be loaded.");
			const body = await response.json();
			const context = body.message || {};
			const students = context.students || [];

			if (!students.length) {
				status.textContent = "No verified Student or Guardian relationship is linked to this account.";
				return;
			}

			status.hidden = true;
			root.hidden = false;
			root.innerHTML = students.map(studentPanel).join("");
		} catch (error) {
			status.textContent = error?.message || "Results could not be loaded.";
			status.classList.add("is-error");
		}
	}

	load();
})();

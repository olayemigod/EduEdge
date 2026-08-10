const STYLE_ID = "eduedge-instructor-assignment-visual-styles";

export function installInstructorAssignmentVisualStyles() {
	if (typeof document === "undefined" || document.getElementById(STYLE_ID)) return;

	const style = document.createElement("style");
	style.id = STYLE_ID;
	style.textContent = `
		.eduedge-instructor-assignments-root {
			--eduedge-assignment-border: var(--edge-color-border, #d8e2ee);
			--eduedge-assignment-border-strong: var(--edge-color-border-strong, #c5d2e1);
			--eduedge-assignment-ink: var(--edge-color-ink-800, #27364a);
			--eduedge-assignment-muted: var(--edge-color-ink-500, #687a90);
			--eduedge-assignment-surface: var(--edge-color-surface, #fff);
			--eduedge-assignment-subtle: var(--edge-color-surface-subtle, #f6f9fc);
			--eduedge-assignment-brand: var(--edge-color-brand-600, #1767b0);
			--eduedge-assignment-brand-soft: var(--edge-color-brand-50, #eef6ff);
		}

		.eduedge-instructor-assignments-root .assignment-panel,
		.eduedge-instructor-assignments-root .assignment-row {
			border-color: var(--eduedge-assignment-border);
			border-radius: 14px;
			box-shadow: 0 1px 2px rgb(15 23 42 / 3%);
		}

		.eduedge-instructor-assignments-root .assignment-row {
			border-left: 4px solid var(--eduedge-assignment-brand);
		}

		.eduedge-instructor-assignments-root .assignment-heading h2,
		.eduedge-instructor-assignments-root .assignment-heading h3 {
			color: var(--eduedge-assignment-ink);
			font-weight: 800;
			letter-spacing: -.015em;
		}

		.eduedge-instructor-assignments-root .edge-eyebrow {
			font-size: .7rem;
			font-weight: 800;
			letter-spacing: .08em;
			text-transform: uppercase;
		}

		.eduedge-instructor-assignments-root .instructor-field > span,
		.eduedge-instructor-assignments-root .row-grid label > span {
			color: var(--eduedge-assignment-ink);
			font-size: .76rem;
			font-weight: 800;
			letter-spacing: .012em;
			line-height: 1.3;
		}

		.eduedge-instructor-assignments-root .row-grid label > small,
		.eduedge-instructor-assignments-root .instructor-field > small {
			color: var(--eduedge-assignment-muted);
			font-size: .72rem;
			font-weight: 500;
			line-height: 1.4;
		}

		.eduedge-instructor-assignments-root .form-control {
			background: var(--eduedge-assignment-surface);
			border: 1px solid var(--eduedge-assignment-border-strong);
			border-radius: 9px;
			box-shadow: none;
			min-height: 2.55rem;
			transition: border-color .15s ease, box-shadow .15s ease, background .15s ease;
		}

		.eduedge-instructor-assignments-root .form-control:focus {
			border-color: var(--edge-color-brand-500, #2e7bc4);
			box-shadow: 0 0 0 3px rgb(46 123 196 / 13%);
			outline: none;
		}

		.eduedge-instructor-assignments-root .form-control:disabled {
			background: var(--eduedge-assignment-subtle);
			cursor: not-allowed;
			opacity: .72;
		}

		.eduedge-instructor-assignments-root .multi-select {
			min-height: 8.25rem;
			padding: .4rem;
		}

		.eduedge-instructor-assignments-root .assignment-actions {
			gap: .5rem;
		}

		.eduedge-instructor-assignments-root .assignment-actions .edge-button,
		.eduedge-instructor-assignments-root .edge-action-bar .edge-button {
			align-items: center;
			background: var(--eduedge-assignment-surface);
			border: 1px solid var(--eduedge-assignment-border-strong);
			border-radius: 9px;
			color: var(--eduedge-assignment-ink);
			display: inline-flex;
			font-size: .76rem;
			font-weight: 800;
			justify-content: center;
			line-height: 1.15;
			min-height: 2.35rem;
			padding: .52rem .78rem;
			transition: background .15s ease, border-color .15s ease, box-shadow .15s ease, color .15s ease, transform .15s ease;
		}

		.eduedge-instructor-assignments-root .assignment-actions .edge-button:not(:disabled):hover,
		.eduedge-instructor-assignments-root .edge-action-bar .edge-button:not(:disabled):hover {
			background: var(--eduedge-assignment-brand-soft);
			border-color: var(--edge-color-brand-300, #9bc6ec);
			color: var(--eduedge-assignment-brand);
			transform: translateY(-1px);
		}

		.eduedge-instructor-assignments-root .assignment-actions .edge-button:focus-visible,
		.eduedge-instructor-assignments-root .edge-action-bar .edge-button:focus-visible {
			box-shadow: 0 0 0 3px rgb(46 123 196 / 16%);
			outline: none;
		}

		.eduedge-instructor-assignments-root .assignment-actions .edge-button:disabled,
		.eduedge-instructor-assignments-root .edge-action-bar .edge-button:disabled {
			cursor: not-allowed;
			opacity: .52;
			transform: none;
		}

		.eduedge-instructor-assignments-root .edge-button--primary {
			background: var(--eduedge-assignment-brand) !important;
			border-color: var(--eduedge-assignment-brand) !important;
			color: #fff !important;
			box-shadow: 0 .25rem .65rem rgb(23 103 176 / 16%);
		}

		.eduedge-instructor-assignments-root .edge-button--primary:not(:disabled):hover {
			background: var(--edge-color-brand-700, #12558f) !important;
			border-color: var(--edge-color-brand-700, #12558f) !important;
			color: #fff !important;
		}

		.eduedge-instructor-assignments-root [data-eduedge-replace-assignment] {
			background: var(--edge-color-warning-50, #fff8e6) !important;
			border-color: var(--edge-color-warning-300, #edc56b) !important;
			color: var(--edge-color-warning-800, #775317) !important;
		}

		.eduedge-instructor-assignments-root [data-eduedge-replace-assignment]:not(:disabled):hover {
			background: var(--edge-color-warning-100, #fff0c6) !important;
			border-color: var(--edge-color-warning-400, #daa841) !important;
		}

		.eduedge-instructor-assignments-root [data-eduedge-replacement-relation] {
			align-items: center;
			background: var(--eduedge-assignment-brand-soft);
			border: 1px solid var(--edge-color-brand-100, #d9ebfb);
			border-radius: 8px;
			color: var(--eduedge-assignment-brand);
			display: flex;
			flex-wrap: wrap;
			font-size: .72rem;
			font-weight: 700;
			gap: .25rem;
			margin-top: .28rem;
			padding: .35rem .48rem;
			width: fit-content;
		}

		.eduedge-instructor-assignments-root [data-eduedge-replacement-relation] button {
			background: transparent;
			border: 0;
			color: inherit;
			cursor: pointer;
			font-size: .72rem;
			font-weight: 800;
			padding: 0;
			text-decoration: underline;
			text-underline-offset: 2px;
		}

		.eduedge-instructor-assignments-root .row-summary {
			gap: .4rem;
		}

		.eduedge-instructor-assignments-root .row-summary span {
			background: var(--eduedge-assignment-subtle);
			border: 1px solid var(--eduedge-assignment-border);
			border-radius: 999px;
			color: var(--eduedge-assignment-muted);
			font-size: .7rem;
			font-weight: 700;
			padding: .3rem .55rem;
		}

		.eduedge-instructor-assignments-root .row-note {
			background: var(--edge-color-info-50, #f2f8fd);
			border-color: var(--edge-color-info-200, #c7def2);
			border-radius: 10px;
			padding: .8rem;
		}

		.eduedge-instructor-assignments-root .row-note strong {
			color: var(--eduedge-assignment-ink);
			font-size: .78rem;
			font-weight: 800;
		}

		.eduedge-instructor-assignments-root .register-list article,
		.eduedge-instructor-assignments-root .branch-eligibility-group,
		.eduedge-instructor-assignments-root .branch-period-row,
		.eduedge-instructor-assignments-root .preview-list,
		.eduedge-instructor-assignments-root .preview-metrics > div {
			border-color: var(--eduedge-assignment-border);
			border-radius: 10px;
		}

		.eduedge-instructor-assignments-root .register-list article {
			background: var(--eduedge-assignment-surface);
			padding: .82rem;
		}

		.eduedge-instructor-assignments-root .register-list article > span > strong {
			color: var(--eduedge-assignment-ink);
			font-size: .86rem;
			font-weight: 800;
			line-height: 1.4;
		}

		.eduedge-instructor-assignments-root .register-list small,
		.eduedge-instructor-assignments-root .branch-eligibility-heading small,
		.eduedge-instructor-assignments-root .branch-period-row small {
			color: var(--eduedge-assignment-muted);
			font-size: .72rem;
			line-height: 1.4;
		}

		.eduedge-instructor-assignments-root .preview-metrics span {
			font-size: .7rem;
			font-weight: 700;
			letter-spacing: .02em;
		}

		.eduedge-instructor-assignments-root .preview-metrics strong {
			color: var(--eduedge-assignment-ink);
			font-weight: 800;
		}

		@media (max-width: 600px) {
			.eduedge-instructor-assignments-root .assignment-actions {
				align-items: stretch;
				width: 100%;
			}
			.eduedge-instructor-assignments-root .assignment-actions .edge-button,
			.eduedge-instructor-assignments-root .edge-action-bar .edge-button {
				flex: 1 1 auto;
			}
		}
	`;
	document.head.appendChild(style);
}

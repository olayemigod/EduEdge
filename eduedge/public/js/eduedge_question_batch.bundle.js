import EduEdgeQuestionBatch from "./eduedge_question_batch/EduEdgeQuestionBatch.vue";
import { installBatchQuestionRichTextEditors } from "./eduedge_question_batch/batch_rich_text_editor";
import "./eduedge_question_builder/rich_text_editor.css";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";


const baseMethods = EduEdgeQuestionBatch.methods || {};
const EnhancedQuestionBatch = {
	name: "EduEdgeQuestionBatch",
	extends: EduEdgeQuestionBatch,
	data() {
		return {
			eduedgeCanUpload: false,
			eduedgeUploadAccessResolved: false,
		};
	},
	methods: {
		addQuestion(...args) {
			const before = this.questions.length;
			const result = baseMethods.addQuestion.apply(this, args);
			if (this.questions.length > before) {
				const newest = this.questions.pop();
				this.questions.unshift(newest);
				this.$nextTick(() => {
					window.requestAnimationFrame(() => {
						this.$el?.querySelector(".eduedge-question-card input.form-control")?.focus();
					});
				});
			}
			return result;
		},
		setMode(mode, ...args) {
			if (mode === "upload" && (!this.eduedgeUploadAccessResolved || !this.eduedgeCanUpload)) return;
			return baseMethods.setMode.call(this, mode, ...args);
		},
	},
};


function resolveMountRoot(target) {
	if (target instanceof Element) return target;
	if (typeof target === "string") return document.querySelector(target);
	return null;
}


function installUploadPermissionGuard(root, viewModel) {
	if (!root || !viewModel) return { destroy() {} };
	let destroyed = false;
	let scheduled = false;
	const requestedUpload = new URL(window.location.href).searchParams.get("mode") === "upload";

	const applyVisibility = () => {
		scheduled = false;
		if (destroyed || !root.isConnected) return;
		const uploadTab = root.querySelectorAll(".eduedge-batch-tabs button")[1];
		if (uploadTab) {
			const visible = Boolean(viewModel.eduedgeUploadAccessResolved && viewModel.eduedgeCanUpload);
			uploadTab.hidden = !visible;
			uploadTab.setAttribute("aria-hidden", visible ? "false" : "true");
		}
		if ((!viewModel.eduedgeUploadAccessResolved || !viewModel.eduedgeCanUpload) && viewModel.mode === "upload") {
			baseMethods.setMode.call(viewModel, "entry");
		}
	};

	const scheduleVisibility = () => {
		if (scheduled || destroyed) return;
		scheduled = true;
		window.requestAnimationFrame(applyVisibility);
	};

	const observer = new MutationObserver(scheduleVisibility);
	observer.observe(root, { childList: true, subtree: true });
	scheduleVisibility();

	frappe.call("eduedge.api.question_batch_safe.get_question_upload_access")
		.then((response) => {
			if (destroyed) return;
			viewModel.eduedgeCanUpload = Boolean(response.message?.can_upload);
			viewModel.eduedgeUploadAccessResolved = true;
			if (viewModel.eduedgeCanUpload && requestedUpload) {
				baseMethods.setMode.call(viewModel, "upload");
			}
			scheduleVisibility();
		})
		.catch(() => {
			if (destroyed) return;
			viewModel.eduedgeCanUpload = false;
			viewModel.eduedgeUploadAccessResolved = true;
			if (viewModel.mode === "upload") baseMethods.setMode.call(viewModel, "entry");
			scheduleVisibility();
		});

	return {
		destroy() {
			destroyed = true;
			observer.disconnect();
		},
	};
}


export function createEduEdgeQuestionBatchApp(rootProps = null) {
	const app = createEduEdgeApp(EnhancedQuestionBatch, rootProps);
	const originalMount = app.mount.bind(app);
	const originalUnmount = app.unmount.bind(app);
	let richEditors = null;
	let uploadGuard = null;

	app.mount = (target, ...args) => {
		const mounted = originalMount(target, ...args);
		const root = resolveMountRoot(target);
		richEditors?.destroy();
		uploadGuard?.destroy();
		richEditors = installBatchQuestionRichTextEditors(root);
		uploadGuard = installUploadPermissionGuard(root, mounted);
		return mounted;
	};

	app.unmount = (...args) => {
		richEditors?.destroy();
		uploadGuard?.destroy();
		richEditors = null;
		uploadGuard = null;
		return originalUnmount(...args);
	};

	return app;
}


if (typeof window !== "undefined") {
	window.EduEdgeQuestionBatch = EnhancedQuestionBatch;
	window.createEduEdgeQuestionBatchApp = createEduEdgeQuestionBatchApp;
}

export default EnhancedQuestionBatch;

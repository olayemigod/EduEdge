const API_ROOT = "eduedge.api.programme_curriculum_governance";

function programmeName(proxy) {
	return proxy?.selectedProgramme?.name || "";
}

async function refresh(proxy) {
	const name = programmeName(proxy);
	if (name && typeof proxy.loadCurriculum === "function") {
		await proxy.loadCurriculum(name);
	}
}

function showError(error) {
	const message = error?.message || error?._server_messages || String(error || __("Curriculum action failed."));
	frappe.msgprint({ title: __("Curriculum action failed"), message, indicator: "red" });
}

function configuredRows(proxy) {
	return Array.isArray(proxy?.filteredConfiguredCourses) ? proxy.filteredConfiguredCourses : [];
}

function addConfiguredControls(root, proxy) {
	const nodes = root.querySelectorAll(".eduedge-programme-course-row");
	const rows = configuredRows(proxy);
	nodes.forEach((node, index) => {
		const course = rows[index];
		if (!course || node.querySelector(".eduedge-curriculum-governance-actions")) return;

		const actions = document.createElement("span");
		actions.className = "eduedge-curriculum-governance-actions";

		const requirement = document.createElement("select");
		requirement.className = "form-control eduedge-curriculum-requirement";
		requirement.setAttribute("aria-label", __("Required or Optional"));
		requirement.innerHTML = `<option value="1">${__("Required")}</option><option value="0">${__("Optional")}</option>`;
		requirement.value = Number(course.required) ? "1" : "0";
		requirement.addEventListener("change", async () => {
			requirement.disabled = true;
			try {
				await frappe.xcall(`${API_ROOT}.update_programme_course_requirement`, {
					programme: programmeName(proxy),
					course: course.name,
					required: requirement.value,
				});
				frappe.show_alert({ message: __("Curriculum requirement updated"), indicator: "green" });
				await refresh(proxy);
			} catch (error) {
				requirement.value = Number(course.required) ? "1" : "0";
				showError(error);
			} finally {
				requirement.disabled = false;
			}
		});

		const remove = document.createElement("button");
		remove.type = "button";
		remove.className = "edge-button eduedge-curriculum-remove";
		remove.textContent = __("Remove");
		remove.addEventListener("click", () => {
			frappe.confirm(
				__("Remove {0} from {1}? This removes it from this Class curriculum only. The Subject master will not be deleted.", [
					course.course_name || course.name,
					proxy.selectedProgramme?.program_name || programmeName(proxy),
				]),
				async () => {
					remove.disabled = true;
					try {
						await frappe.xcall(`${API_ROOT}.remove_programme_course`, {
							programme: programmeName(proxy),
							course: course.name,
						});
						frappe.show_alert({ message: __("Subject removed from Class curriculum"), indicator: "green" });
						await refresh(proxy);
					} catch (error) {
						showError(error);
					} finally {
						remove.disabled = false;
					}
				}
			);
		});

		actions.append(requirement, remove);
		node.appendChild(actions);
	});
}

function addAvailableControls(root, proxy) {
	const heading = [...root.querySelectorAll(".eduedge-programme-section-heading")].find((node) =>
		node.textContent.includes(__("Available Institution"))
	);
	if (!heading || heading.querySelector(".eduedge-curriculum-add-governance")) return;

	const original = [...heading.querySelectorAll("button")].find((button) => button.textContent.includes(__("Add selected")));
	if (original) original.style.display = "none";

	const controls = document.createElement("span");
	controls.className = "eduedge-curriculum-add-governance";

	const requirement = document.createElement("select");
	requirement.className = "form-control";
	requirement.setAttribute("aria-label", __("Add selected as"));
	requirement.innerHTML = `<option value="1">${__("Add as Required")}</option><option value="0">${__("Add as Optional")}</option>`;

	const add = document.createElement("button");
	add.type = "button";
	add.className = "edge-button edge-button--primary";
	const updateLabel = () => {
		const count = Array.isArray(proxy.selectedCurriculumCourses) ? proxy.selectedCurriculumCourses.length : 0;
		add.textContent = __("Add selected ({0})", [count]);
		add.disabled = !count;
	};
	updateLabel();
	add.addEventListener("click", async () => {
		const selected = Array.isArray(proxy.selectedCurriculumCourses) ? [...proxy.selectedCurriculumCourses] : [];
		if (!selected.length) return;
		add.disabled = true;
		try {
			await frappe.xcall(`${API_ROOT}.add_programme_courses`, {
				programme: programmeName(proxy),
				courses: selected,
				required: requirement.value,
			});
			proxy.selectedCurriculumCourses = [];
			frappe.show_alert({ message: __("Subjects added to Class curriculum"), indicator: "green" });
			await refresh(proxy);
		} catch (error) {
			showError(error);
		} finally {
			updateLabel();
		}
	});

	controls.append(requirement, add);
	heading.appendChild(controls);
}

function render(root, proxy) {
	if (!root?.isConnected || !proxy?.selectedProgramme) return;
	addConfiguredControls(root, proxy);
	addAvailableControls(root, proxy);
}

export function installProgrammeCurriculumGovernance(app, root, mountedProxy = null) {
	const proxy = mountedProxy || app?._instance?.proxy;
	if (!proxy || !root) return;
	let scheduled = false;
	const schedule = () => {
		if (scheduled) return;
		scheduled = true;
		window.requestAnimationFrame(() => {
			scheduled = false;
			render(root, proxy);
		});
	};
	const observer = new MutationObserver(schedule);
	observer.observe(root, { childList: true, subtree: true });
	root.addEventListener("change", schedule, true);
	schedule();
	const originalUnmount = app.unmount.bind(app);
	app.unmount = (...args) => {
		observer.disconnect();
		return originalUnmount(...args);
	};
}

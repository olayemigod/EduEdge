function saveErrorMessage(error, fallback) {
	return error?.message || error?._server_messages || fallback;
}

export function installProgrammeModalSaveFix(proxy) {
	if (!proxy) return;
	const context = proxy.$?.ctx || proxy;
	context.saveProgramme = async function saveProgramme() {
		if (!proxy.canSave || proxy.saving) return;
		proxy.saving = true;
		proxy.saveError = "";
		const savedDraft = { ...proxy.draft };
		const label = proxy.editorProgrammeSingular || "Class / Programme";
		try {
			const response = await frappe.call({
				method: "eduedge.api.programmes.save_programme",
				type: "POST",
				args: {
					programme: savedDraft.name || undefined,
					program_name: savedDraft.program_name,
					program_abbreviation: savedDraft.program_abbreviation || undefined,
					institution: savedDraft.eduedge_institution,
					department: savedDraft.department,
				},
			});
			const savedName = String(response?.message?.name || "").trim();
			if (!savedName) throw new Error(__("The server did not return the saved Class identity."));
			await proxy.load(true);
			const row = proxy.data.programmes.find((item) => item.name === savedName);
			proxy.programmeModalOpen = false;
			proxy.draft = { name: "", program_name: "", program_abbreviation: "", department: "", eduedge_institution: "", active_offering_count: 0 };
			frappe.show_alert({ message: __(`${label} saved`), indicator: "green" });
			if (row) await proxy.selectProgramme(row);
		} catch (error) {
			proxy.saveError = saveErrorMessage(error, __(`${label} could not be saved.`));
		} finally {
			proxy.saving = false;
		}
	};
}

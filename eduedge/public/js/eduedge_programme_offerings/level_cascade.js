function programmeSection(programmes, programmeName) {
	return programmes.find((row) => row.name === programmeName)?.eduedge_academic_section || "";
}

function levelsForProgramme(levels, programmes, programmeName) {
	const section = programmeSection(programmes, programmeName);
	if (!section) return [...levels];
	return levels.filter((row) => !row.academic_section || row.academic_section === section);
}

function clearInvalidLevel(target, levels) {
	if (target.academic_level && !levels.some((row) => row.name === target.academic_level)) {
		target.academic_level = "";
	}
}

export function applyProgrammeOfferingLevelCascade(component) {
	const methods = component.methods || {};
	const originalLoad = methods.load;
	const originalLoadDraftOptions = methods.loadDraftOptions;
	const originalApplyFilters = methods.applyFilters;

	component.methods = {
		...methods,
		applyFilterLevelCascade() {
			const source = this.__eduedgeAllFilterLevels || this.data.options.levels || [];
			if (!this.__eduedgeAllFilterLevels) this.__eduedgeAllFilterLevels = [...source];
			const filtered = levelsForProgramme(source, this.data.options.programmes || [], this.filters.program);
			this.data.options.levels = filtered;
			clearInvalidLevel(this.filters, filtered);
		},
		applyDraftLevelCascade() {
			const source = this.__eduedgeAllDraftLevels || this.draftOptions.levels || [];
			if (!this.__eduedgeAllDraftLevels) this.__eduedgeAllDraftLevels = [...source];
			const filtered = levelsForProgramme(source, this.draftOptions.programmes || [], this.draft.program);
			this.draftOptions.levels = filtered;
			clearInvalidLevel(this.draft, filtered);
		},
		async load(...args) {
			const result = await originalLoad.apply(this, args);
			this.__eduedgeAllFilterLevels = [...(this.data.options.levels || [])];
			this.applyFilterLevelCascade();
			return result;
		},
		async loadDraftOptions(...args) {
			const result = await originalLoadDraftOptions.apply(this, args);
			this.__eduedgeAllDraftLevels = [...(this.draftOptions.levels || [])];
			this.applyDraftLevelCascade();
			return result;
		},
		applyFilters(...args) {
			this.applyFilterLevelCascade();
			return originalApplyFilters.apply(this, args);
		},
	};

	component.watch = {
		...(component.watch || {}),
		"draft.program"() {
			this.applyDraftLevelCascade();
		},
		"filters.program"() {
			this.applyFilterLevelCascade();
		},
	};

	return component;
}

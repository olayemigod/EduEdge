from __future__ import annotations

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.no_breadcrumbs = True
	context.show_sidebar = False
	context.title = "EduEdge CBT"
	return context

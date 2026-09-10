import EduEdgeCBTAttemptReview from "./eduedge_cbt_attempt_review/EduEdgeCBTAttemptReview.vue";
import { createEduEdgeApp } from "./eduedge_ui/app_factory";

export function createEduEdgeCBTAttemptReviewApp(rootProps = null) {
	return createEduEdgeApp(EduEdgeCBTAttemptReview, rootProps);
}

if (typeof window !== "undefined") {
	window.EduEdgeCBTAttemptReview = EduEdgeCBTAttemptReview;
	window.createEduEdgeCBTAttemptReviewApp = createEduEdgeCBTAttemptReviewApp;
}

export default EduEdgeCBTAttemptReview;

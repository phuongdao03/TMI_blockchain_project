import { redirect } from "next/navigation";

/**
 * Compatibility redirect for old bookmarks. Similarity comparison is no
 * longer a standalone reviewer task; reviewers continue in the main queue.
 */
export default function RetiredSimilarityReviewPage() {
  redirect("/reviews");
}

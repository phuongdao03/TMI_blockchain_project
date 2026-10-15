"use client";

import type { CommunityInteractionPost } from "@/components/community/community-post-actions";
import { CommunityCommentThreads } from "@/components/community/community-comment-threads";
import { CommunityPostActions } from "@/components/community/community-post-actions";

export function CommunityPostEngagement({
  post,
}: {
  post: CommunityInteractionPost;
}) {
  return (
    <>
      <CommunityPostActions post={post} />
      <CommunityCommentThreads
        postId={post.id}
        commentCount={post.commentCount}
      />
    </>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";

type AdaptiveVideoProps = {
  fallbackUrl: string;
  streamingUrl?: string | null;
  poster?: string;
  autoPlay?: boolean;
  controls?: boolean;
  controlsList?: string;
  loop?: boolean;
  muted?: boolean;
  className?: string;
};

export function AdaptiveVideo({
  fallbackUrl,
  streamingUrl,
  poster,
  autoPlay = false,
  controls = true,
  controlsList,
  loop = false,
  muted = false,
  className,
}: AdaptiveVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [nearViewport, setNearViewport] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (typeof IntersectionObserver === "undefined") {
      const fallbackTimer = setTimeout(() => setNearViewport(true), 0);
      return () => clearTimeout(fallbackTimer);
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) setNearViewport(true);
      },
      { rootMargin: "240px" },
    );
    observer.observe(video);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !nearViewport) return;
    if (!streamingUrl) {
      video.src = fallbackUrl;
      return;
    }
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = streamingUrl;
      return;
    }

    let disposed = false;
    let destroy: (() => void) | undefined;
    void import("hls.js")
      .then(({ default: Hls }) => {
        if (disposed) return;
        if (!Hls.isSupported()) {
          video.src = fallbackUrl;
          return;
        }
        const hls = new Hls({
          backBufferLength: 30,
          capLevelToPlayerSize: true,
          enableWorker: true,
          maxBufferLength: 30,
          startLevel: -1,
        });
        hls.loadSource(streamingUrl);
        hls.attachMedia(video);
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (!data.fatal) return;
          hls.destroy();
          video.src = fallbackUrl;
          video.load();
        });
        destroy = () => hls.destroy();
      })
      .catch(() => {
        if (disposed) return;
        video.src = fallbackUrl;
        video.load();
      });
    return () => {
      disposed = true;
      destroy?.();
    };
  }, [fallbackUrl, nearViewport, streamingUrl]);

  return (
    <video
      autoPlay={autoPlay}
      className={className}
      controls={controls}
      controlsList={controlsList}
      loop={loop}
      muted={muted}
      playsInline
      poster={poster}
      preload={nearViewport ? "metadata" : "none"}
      ref={videoRef}
    >
      <track kind="captions" />
    </video>
  );
}

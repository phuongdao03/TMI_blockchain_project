"use client";

import { Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";

type AdaptiveVideoProps = {
  fallbackUrl: string;
  streamingUrl?: string | null;
  poster?: string;
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
  controls = true,
  controlsList,
  loop = false,
  muted = false,
  className,
}: AdaptiveVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const usingStreaming = useRef(false);
  const destroyStreaming = useRef<(() => void) | null>(null);
  const startupTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [active, setActive] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    return () => {
      if (startupTimeout.current) clearTimeout(startupTimeout.current);
      destroyStreaming.current?.();
      destroyStreaming.current = null;
      usingStreaming.current = false;
    };
  }, [fallbackUrl, streamingUrl]);

  function startPlayback() {
    const video = videoRef.current;
    if (!video) return;
    destroyStreaming.current?.();
    destroyStreaming.current = null;
    usingStreaming.current = false;
    if (startupTimeout.current) clearTimeout(startupTimeout.current);
    setFailed(false);
    setActive(true);
    video.src = fallbackUrl;
    video.load();
    void video.play().catch(() => undefined);
    startupTimeout.current = setTimeout(() => {
      if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
        void tryStreaming();
      }
    }, 12000);
  }

  async function tryStreaming() {
    const video = videoRef.current;
    if (!video || !streamingUrl || usingStreaming.current) {
      setFailed(true);
      return;
    }
    if (startupTimeout.current) clearTimeout(startupTimeout.current);
    usingStreaming.current = true;
    setFailed(false);
    startupTimeout.current = setTimeout(() => {
      if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
        setFailed(true);
      }
    }, 15000);
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = streamingUrl;
      video.load();
      return;
    }
    try {
      const { default: Hls } = await import("hls.js");
      if (!videoRef.current || !Hls.isSupported()) {
        setFailed(true);
        return;
      }
      const hls = new Hls({
        backBufferLength: 10,
        capLevelToPlayerSize: true,
        enableWorker: true,
        maxBufferLength: 10,
        startLevel: 0,
      });
      hls.loadSource(streamingUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) setFailed(true);
      });
      destroyStreaming.current = () => hls.destroy();
    } catch {
      setFailed(true);
    }
  }

  return (
    <div className="relative grid size-full place-items-center bg-[#1d0e0b]">
      <video
        className={className}
        controls={active && controls}
        controlsList={controlsList}
        loop={loop}
        muted={muted}
        onError={() => void tryStreaming()}
        onCanPlay={() => {
          if (startupTimeout.current) clearTimeout(startupTimeout.current);
          if (active)
            void videoRef.current?.play().catch(() => setFailed(true));
        }}
        playsInline
        poster={poster}
        preload="none"
        ref={videoRef}
      >
        <track kind="captions" />
      </video>
      {!active || failed ? (
        <button
          aria-label={failed ? "Thử phát lại video" : "Phát video tác phẩm"}
          className="absolute inset-0 grid place-items-center bg-black/15 text-white transition hover:bg-black/25"
          onClick={startPlayback}
          type="button"
        >
          <span className="grid size-16 place-items-center rounded-full border border-white/70 bg-[#680b17]/90 shadow-xl">
            <Play aria-hidden="true" className="ml-1 size-7 fill-current" />
          </span>
          {failed ? (
            <span className="mt-20 rounded bg-black/70 px-3 py-2 text-sm font-semibold">
              Video chưa phát được. Chạm để thử lại.
            </span>
          ) : null}
        </button>
      ) : null}
    </div>
  );
}

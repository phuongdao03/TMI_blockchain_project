"use client";

import { LoaderCircle, Play } from "lucide-react";
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
  const playRequested = useRef(false);
  const destroyStreaming = useRef<(() => void) | null>(null);
  const startupTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [active, setActive] = useState(false);
  const [warmed, setWarmed] = useState(false);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const video = videoRef.current;
    if (
      !video ||
      streamingUrl ||
      typeof IntersectionObserver === "undefined" ||
      window.matchMedia?.("(pointer: coarse)").matches
    )
      return;
    setWarmed(false);

    const connection = (
      navigator as Navigator & {
        connection?: { saveData?: boolean; effectiveType?: string };
      }
    ).connection;
    if (
      connection?.saveData ||
      connection?.effectiveType === "slow-2g" ||
      connection?.effectiveType === "2g"
    )
      return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        observer.disconnect();
        if (playRequested.current) return;
        video.preload = "metadata";
        video.src = fallbackUrl;
        video.load();
        setWarmed(true);
      },
      { rootMargin: "350px" },
    );
    observer.observe(video);
    return () => observer.disconnect();
  }, [fallbackUrl, streamingUrl]);

  useEffect(() => {
    return () => {
      if (startupTimeout.current) clearTimeout(startupTimeout.current);
      destroyStreaming.current?.();
      destroyStreaming.current = null;
      usingStreaming.current = false;
      playRequested.current = false;
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
    setLoading(true);
    setActive(true);
    playRequested.current = true;
    if (streamingUrl) {
      void tryStreaming();
      return;
    }
    startFallback();
  }

  function startFallback() {
    const video = videoRef.current;
    if (!video) return;
    if (startupTimeout.current) clearTimeout(startupTimeout.current);
    destroyStreaming.current?.();
    destroyStreaming.current = null;
    usingStreaming.current = false;
    if (video.getAttribute("src") !== fallbackUrl || video.error) {
      video.src = fallbackUrl;
      video.load();
    }
    void video.play().catch(() => undefined);
  }

  async function tryStreaming() {
    const video = videoRef.current;
    if (!video || !streamingUrl || usingStreaming.current) return;
    if (startupTimeout.current) clearTimeout(startupTimeout.current);
    usingStreaming.current = true;
    setFailed(false);
    setLoading(true);
    startupTimeout.current = setTimeout(() => {
      if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA)
        startFallback();
    }, 3000);
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = streamingUrl;
      video.load();
      return;
    }
    try {
      const { default: Hls } = await import("hls.js");
      if (!videoRef.current || !usingStreaming.current) return;
      if (!Hls.isSupported()) {
        startFallback();
        return;
      }
      const hls = new Hls({
        backBufferLength: 10,
        capLevelToPlayerSize: true,
        enableWorker: true,
        maxBufferLength: 10,
        startLevel: 0,
      });
      destroyStreaming.current = () => hls.destroy();
      hls.loadSource(streamingUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) startFallback();
      });
    } catch {
      startFallback();
    }
  }

  return (
    <div className="adaptive-video relative grid size-full place-items-center bg-[#1d0e0b]">
      <video
        className={className}
        controls={active && !failed && controls}
        controlsList={controlsList}
        loop={loop}
        muted={muted}
        onError={() => {
          if (!playRequested.current) return;
          if (usingStreaming.current) startFallback();
          else {
            setFailed(true);
            setLoading(false);
          }
        }}
        onCanPlay={() => {
          if (startupTimeout.current) clearTimeout(startupTimeout.current);
          setLoading(false);
          if (active) void videoRef.current?.play().catch(() => undefined);
        }}
        onPlaying={() => {
          if (startupTimeout.current) clearTimeout(startupTimeout.current);
          setFailed(false);
          setLoading(false);
        }}
        onWaiting={() => setLoading(true)}
        onStalled={() => {
          if (playRequested.current) {
            setLoading(true);
            if (usingStreaming.current) {
              if (startupTimeout.current) clearTimeout(startupTimeout.current);
              startupTimeout.current = setTimeout(startFallback, 3000);
            }
          }
        }}
        playsInline
        poster={poster}
        preload={warmed || active ? "metadata" : "none"}
        ref={videoRef}
      >
        <track kind="captions" />
      </video>
      {active && !failed && loading ? (
        <span
          className="adaptive-video__loading pointer-events-none absolute inset-0 grid place-items-center bg-black/45 text-white"
          role="status"
        >
          <span className="flex flex-col items-center gap-3 rounded-lg bg-black/75 px-5 py-4 text-sm font-semibold">
            <LoaderCircle
              aria-hidden="true"
              className="size-7 animate-spin motion-reduce:animate-none"
            />
            Đang tải video…
          </span>
        </span>
      ) : null}
      {!active || failed ? (
        <button
          aria-label={failed ? "Thử phát lại video" : "Phát video tác phẩm"}
          className="adaptive-video__play absolute inset-0 grid place-items-center bg-black/15 text-white transition hover:bg-black/25"
          onClick={startPlayback}
          type="button"
        >
          <span className="grid size-16 place-items-center rounded-full border border-white/70 bg-[#680b17]/90 shadow-xl">
            <Play aria-hidden="true" className="ml-1 size-7 fill-current" />
          </span>
          {failed ? (
            <span className="adaptive-video__error mt-20 rounded bg-black/70 px-3 py-2 text-sm font-semibold">
              Video chưa phát được. Chạm để thử lại.
            </span>
          ) : null}
        </button>
      ) : null}
    </div>
  );
}

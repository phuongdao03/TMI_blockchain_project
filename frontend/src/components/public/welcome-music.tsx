"use client";

import { Music2, Pause, Play } from "lucide-react";
import { useRef, useState } from "react";

export function WelcomeMusic() {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolume] = useState(0.5);

  function togglePlayback() {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      audio.volume = volume;
      setPlaying(true);
      void audio.play().catch(() => setPlaying(false));
    }
  }

  return (
    <div className="welcome-music">
      <audio
        aria-label="Bản hùng ca Tinh Hoa Việt"
        loop
        onEnded={() => setPlaying(false)}
        onPause={() => setPlaying(false)}
        preload="none"
        ref={audioRef}
        src="/assets/institution/welcome.mp3"
      />
      <button
        aria-label={playing ? "Tạm dừng bản hùng ca" : "Phát bản hùng ca"}
        className="welcome-music__play"
        onClick={togglePlayback}
        type="button"
      >
        {playing ? (
          <Pause aria-hidden="true" size={20} />
        ) : (
          <Play aria-hidden="true" size={20} />
        )}
      </button>
      <div className="welcome-music__label">
        <strong>Bản hùng ca Tinh Hoa Việt</strong>
        <span>{playing ? "Đang phát" : "Nhấn để nghe nhạc chào mừng"}</span>
      </div>
      <Music2 aria-hidden="true" className="welcome-music__icon" size={22} />
      <label className="sr-only" htmlFor="welcome-music-volume">
        Âm lượng nhạc chào mừng
      </label>
      <input
        id="welcome-music-volume"
        max="1"
        min="0"
        onChange={(event) => {
          const next = Number(event.target.value);
          setVolume(next);
          if (audioRef.current) audioRef.current.volume = next;
        }}
        step="0.05"
        type="range"
        value={volume}
      />
    </div>
  );
}

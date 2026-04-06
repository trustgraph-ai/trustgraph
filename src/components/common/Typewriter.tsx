import { useState, useEffect, useRef } from "react";

interface TypewriterProps {
  text: string;
  speed?: number;
  onDone?: () => void;
}

export function Typewriter({ text, speed = 12, onDone }: TypewriterProps) {
  const [displayed, setDisplayed] = useState("");
  const idx = useRef(0);

  useEffect(() => {
    idx.current = 0;
    setDisplayed("");
    const interval = setInterval(() => {
      idx.current++;
      if (idx.current >= text.length) {
        setDisplayed(text);
        clearInterval(interval);
        onDone?.();
      } else {
        setDisplayed(text.slice(0, idx.current));
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed, onDone]);

  return (
    <span>
      {displayed}
      <span style={{ opacity: displayed.length < text.length ? 1 : 0, color: "#FCD34D" }}>
        ▌
      </span>
    </span>
  );
}

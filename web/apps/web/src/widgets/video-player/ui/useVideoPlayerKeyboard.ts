import { useEffect, useState, type RefObject } from "react";

interface UseVideoPlayerKeyboardOptions {
  playerRef: RefObject<HTMLElement | null>;
  currentTime: number;
  volume: number;
  onPlayPause: () => void;
  onSeek: (seconds: number) => void;
  onVolumeChange: (value: number) => void;
  onMuteToggle: () => void;
  onFullscreenToggle: () => void;
  onControlsShow: () => void;
}

export function useVideoPlayerKeyboard({
  playerRef,
  currentTime,
  volume,
  onPlayPause,
  onSeek,
  onVolumeChange,
  onMuteToggle,
  onFullscreenToggle,
  onControlsShow,
}: UseVideoPlayerKeyboardOptions): void {
  const [keyboardActive, setKeyboardActive] = useState(true);

  useEffect(() => {
    const player = playerRef.current;
    const activeElement = document.activeElement;

    if (
      !player ||
      (activeElement instanceof HTMLElement && isTextEditingTarget(activeElement))
    ) {
      return;
    }

    player.focus({ preventScroll: true });
  }, [playerRef]);

  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      const target = getHTMLElement(event.target);
      setKeyboardActive(!isTextEditingTarget(target));
    };

    const handleFocusIn = (event: FocusEvent) => {
      const target = getHTMLElement(event.target);
      setKeyboardActive(!isTextEditingTarget(target));
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        !keyboardActive ||
        event.defaultPrevented ||
        event.ctrlKey ||
        event.metaKey ||
        event.altKey
      ) {
        return;
      }

      const player = playerRef.current;
      const target = getHTMLElement(event.target);
      if (!player || !target || isTextEditingTarget(target)) {
        return;
      }

      const isInsidePlayer = player.contains(target);

      if (isInsidePlayer && isKeyboardOwnedControl(target)) {
        return;
      }

      if (
        !isInsidePlayer &&
        (event.key === "ArrowUp" || event.key === "ArrowDown")
      ) {
        return;
      }

      if (
        !isInsidePlayer &&
        isExternalPressTarget(target) &&
        (event.key === " " || event.key === "Enter")
      ) {
        return;
      }

      switch (event.key) {
        case " ":
        case "k":
        case "K":
          event.preventDefault();
          onPlayPause();
          onControlsShow();
          break;
        case "ArrowLeft":
          event.preventDefault();
          onSeek(currentTime - 5);
          onControlsShow();
          break;
        case "ArrowRight":
          event.preventDefault();
          onSeek(currentTime + 5);
          onControlsShow();
          break;
        case "ArrowUp":
          event.preventDefault();
          onVolumeChange(volume + 0.05);
          onControlsShow();
          break;
        case "ArrowDown":
          event.preventDefault();
          onVolumeChange(volume - 0.05);
          onControlsShow();
          break;
        case "m":
        case "M":
          event.preventDefault();
          onMuteToggle();
          onControlsShow();
          break;
        case "f":
        case "F":
          event.preventDefault();
          onFullscreenToggle();
          onControlsShow();
          break;
        case "Escape":
          if (document.fullscreenElement === player) {
            event.preventDefault();
            void document.exitFullscreen();
            onControlsShow();
          }
          break;
        default:
          break;
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("focusin", handleFocusIn);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("focusin", handleFocusIn);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [
    currentTime,
    keyboardActive,
    onControlsShow,
    onFullscreenToggle,
    onMuteToggle,
    onPlayPause,
    onSeek,
    onVolumeChange,
    playerRef,
    volume,
  ]);
}

function getHTMLElement(target: EventTarget | null): HTMLElement | null {
  return target instanceof HTMLElement ? target : null;
}

function isTextEditingTarget(target: HTMLElement | null): boolean {
  if (!target) {
    return false;
  }

  return (
    target.matches("input, textarea, select, [contenteditable='true']") ||
    target.closest("input, textarea, select, [contenteditable='true']") !==
      null
  );
}

function isKeyboardOwnedControl(target: HTMLElement): boolean {
  return (
    target.closest(
      [
        "button",
        "a[href]",
        "input",
        "textarea",
        "select",
        "[contenteditable='true']",
        "[role='button']",
        "[role='checkbox']",
        "[role='combobox']",
        "[role='listbox']",
        "[role='menuitem']",
        "[role='option']",
        "[role='radio']",
        "[role='slider']",
        "[role='spinbutton']",
        "[role='switch']",
      ].join(", "),
    ) !== null
  );
}

function isExternalPressTarget(target: HTMLElement): boolean {
  return (
    target.closest(
      [
        "button",
        "a[href]",
        "[role='button']",
        "[role='checkbox']",
        "[role='menuitem']",
        "[role='radio']",
        "[role='switch']",
      ].join(", "),
    ) !== null
  );
}

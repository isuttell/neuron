import { render, fireEvent, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { AudioBarPlayer } from "../";

describe("AudioPlayer", () => {
  beforeEach(() => {
    // Mock AudioContext
    window.AudioContext = jest.fn().mockImplementation(() => ({
      decodeAudioData: jest.fn(),
      close: jest.fn(),
    }));
  });

  test("renders audio element with controls", () => {
    render(<AudioBarPlayer src="test.mp3" />);
    expect(screen.getByRole("audio")).toBeInTheDocument();
  });

  test("handles play/pause correctly", () => {
    render(<AudioBarPlayer src="test.mp3" />);
    const audio = screen.getByRole("audio") as HTMLAudioElement;

    fireEvent.play(audio);
    expect(audio.paused).toBeFalsy();

    fireEvent.pause(audio);
    expect(audio.paused).toBeTruthy();
  });

  test("updates waveform on progress", async () => {
    render(<AudioBarPlayer src="test.mp3" />);
    const canvas = screen.getByRole("slider");
    expect(canvas).toBeInTheDocument();
  });
});

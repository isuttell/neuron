export interface AudioData {
  waveform: number[];
  duration: number;
  sampleRate: number;
}

export interface WaveformDrawOptions {
  color: string;
  backgroundColor: string;
  progressColor: string;
  lineWidth: number;
}

export interface AudioBarPlayerProps {
  className?: string;
  src: string;
  autoPlay?: boolean;
  preload?: string;
  loop?: boolean;
  children?: React.ReactNode;
  currentProgress?: number;
  waveformData?: number[];
  onEnded?: () => void;
  onPlay?: () => void;
  onPause?: () => void;
  title?: string;
}
